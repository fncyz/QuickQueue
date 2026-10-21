from django.contrib.auth import authenticate
from django.conf import settings
from qq.models import Barangay
from .serializers import BarangaySerializer, DocumentTemplateSerializer

from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from qq.models import Resident
from .serializers import (
    ResidentSerializer,
    RegisterSerializer,
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db import close_old_connections, connection
from django.db.models.deletion import ProtectedError
from django.db.models import CharField, Count, F, Q, Value
from django.db.models.functions import Cast, Concat, ExtractYear, LPad
from django.utils import timezone
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
import logging
import os
import re
import time
import uuid

from qq.models import Appointment, AssistantKnowledge, BarangayServiceConfiguration, BarangayStaff, ChatFeedback, ChatMessage, ChatQuestionTopic, ChatSession, ClosedAppointmentDate, DocumentTemplate, EventBooking, GeneratedDocument, Notification, PushDelivery, PushDevice, QueueTicket, Service, TimeSlot
from qq.services.appointment_service import create_appointment, create_special_service_booking
from qq.services.configuration_service import effective_service_duration, effective_service_fee
from qq.services.timeslot_service import ensure_default_time_slots, regular_daily_capacity, regular_slot_capacities
from qq.services.notification_service import notify_barangay_staff, notify_resident
from qq.services.queue_service import CHECKED_IN_NOTE, live_queue_participation_q
from qq.services.appointment_expiration import (
    appointment_checkin_window_open,
    appointment_expiration_at,
    appointment_start_at,
    expire_overdue_appointments,
    is_appointment_expired,
)
from qq.services.assistant_data import (
    assistant_data_for,
    money_label,
    office_hours,
    queue_snapshot_for,
    service_fee_for,
)
from qq.services.assistant_language import detect_language
from qq.services.assistant_responses import deterministic_reply, provider_failure_reply
from qq.gemini_service import GeminiUnavailable, ask_gemini, check_gemini_ready
from .throttles import AccountDeletionRateThrottle, ChatRateThrottle


logger = logging.getLogger(__name__)


class TransactionsPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 50


def _delete_stored_file_safely(storage, name):
    if not name:
        return
    try:
        storage.delete(name)
    except Exception as error:
        logger.warning(
            "Unable to remove a document-template storage object; error_type=%s.",
            type(error).__name__,
        )


def _storage_failure_response():
    return Response(
        {"template_file": ["The template could not be saved to persistent storage. Please try again."]},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _safe_request_id(request):
    value = request.headers.get("X-Request-ID", "")[:64]
    return value if re.fullmatch(r"[A-Za-z0-9._-]+", value) else "not-provided"


def _template_barangay(request):
    """Return the barangay only for its owner/admin staff."""
    if hasattr(request.user, "barangay_profile"):
        return request.user.barangay_profile
    try:
        staff = request.user.staff_profile
    except BarangayStaff.DoesNotExist:
        return None
    return staff.barangay if staff.role == BarangayStaff.Role.ADMIN else None


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def document_templates_api(request):
    barangay = _template_barangay(request)
    if not barangay:
        return Response({"detail": "Barangay admin access is required."}, status=status.HTTP_403_FORBIDDEN)
    if request.method == "GET":
        templates = DocumentTemplate.objects.filter(barangay=barangay).select_related("service")
        return Response(DocumentTemplateSerializer(templates, many=True, context={"request": request}).data)
    serializer = DocumentTemplateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    service = serializer.validated_data["service"]
    if DocumentTemplate.objects.filter(barangay=barangay, service=service).exists():
        return Response({"service": ["A template already exists for this service. Use replace instead."]}, status=status.HTTP_400_BAD_REQUEST)
    template = DocumentTemplate(
        barangay=barangay,
        uploaded_by=request.user,
        **serializer.validated_data,
    )
    try:
        with transaction.atomic():
            template.save()
    except Exception as error:
        if template.template_file and template.template_file._committed:
            _delete_stored_file_safely(
                template.template_file.storage, template.template_file.name
            )
        logger.error(
            "Document-template upload failed for barangay_id=%s error_type=%s.",
            barangay.pk,
            type(error).__name__,
        )
        return _storage_failure_response()
    return Response(DocumentTemplateSerializer(template, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "PUT", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def document_template_detail_api(request, pk):
    barangay = _template_barangay(request)
    if not barangay:
        return Response({"detail": "Barangay admin access is required."}, status=status.HTTP_403_FORBIDDEN)
    try:
        template = DocumentTemplate.objects.select_related("service").get(pk=pk, barangay=barangay)
    except DocumentTemplate.DoesNotExist:
        return Response({"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response(DocumentTemplateSerializer(template, context={"request": request}).data)
    if request.method == "DELETE":
        storage = template.template_file.storage
        stored_name = template.template_file.name
        try:
            with transaction.atomic():
                template.delete()
        except DatabaseError as error:
            logger.error(
                "Document-template deletion failed for barangay_id=%s template_id=%s error_type=%s.",
                barangay.pk,
                pk,
                type(error).__name__,
            )
            return Response(
                {"detail": "The template could not be deleted. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        _delete_stored_file_safely(storage, stored_name)
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = DocumentTemplateSerializer(template, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    replacing_file = "template_file" in serializer.validated_data
    old_storage = template.template_file.storage
    old_name = template.template_file.name
    if replacing_file:
        template.version += 1
    try:
        with transaction.atomic():
            template = serializer.save()
    except Exception as error:
        new_name = template.template_file.name if template.template_file else ""
        if replacing_file and new_name and new_name != old_name:
            _delete_stored_file_safely(template.template_file.storage, new_name)
        logger.error(
            "Document-template update failed for barangay_id=%s template_id=%s error_type=%s.",
            barangay.pk,
            pk,
            type(error).__name__,
        )
        return _storage_failure_response()
    if replacing_file and old_name and old_name != template.template_file.name:
        _delete_stored_file_safely(old_storage, old_name)
    return Response(DocumentTemplateSerializer(template, context={"request": request}).data)


@api_view(["POST"])
def login_api(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(
        username=username,
        password=password,
    )

    if user is None:
        return Response(
            {
                "success": False,
                "message": "Invalid username or password."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        resident = Resident.objects.get(user=user)
    except Resident.DoesNotExist:
        return Response(
            {"success": False, "message": "Invalid username or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "success": True,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "resident": ResidentSerializer(resident).data,
            "security_setup_stage": resident.security_setup_stage,
        }
    )


@api_view(["POST"])
def pin_login_api(request):
    username = str(request.data.get("username", "")).strip()
    pin = str(request.data.get("pin", ""))
    if not username or not pin.isdigit() or len(pin) != 4:
        return Response({"success": False, "message": "Enter your username and 4-digit PIN."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        resident = Resident.objects.select_related("user").get(user__username__iexact=username)
    except Resident.DoesNotExist:
        return Response({"success": False, "message": "Invalid username or PIN."}, status=status.HTTP_401_UNAUTHORIZED)
    if not resident.user.is_active or resident.security_setup_stage != Resident.SecuritySetupStage.COMPLETE or not resident.pin_hash or not check_password(pin, resident.pin_hash):
        return Response({"success": False, "message": "Invalid username or PIN."}, status=status.HTTP_401_UNAUTHORIZED)
    refresh = RefreshToken.for_user(resident.user)
    return Response({
        "success": True,
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "resident": ResidentSerializer(resident).data,
        "security_setup_stage": resident.security_setup_stage,
    })

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_api(request):
    resident = request.user.resident_profile

    if request.method == "GET" and request.query_params.get("summary") == "1":
        return Response({"username": request.user.username, "first_name": resident.first_name})

    if request.method == "PATCH":
        email = request.data.get("email", "").strip() or None
        contact_number = request.data.get("contact_number", "").strip()
        if not contact_number.isdigit():
            return Response({"message": "Contact number must contain digits only."}, status=status.HTTP_400_BAD_REQUEST)
        if Resident.objects.exclude(pk=resident.pk).filter(contact_number=contact_number).exists():
            return Response({"message": "Contact number is already registered."}, status=status.HTTP_400_BAD_REQUEST)
        if email and Resident.objects.exclude(pk=resident.pk).filter(email__iexact=email).exists():
            return Response({"message": "Email address is already registered."}, status=status.HTTP_400_BAD_REQUEST)
        resident.email = email
        resident.contact_number = contact_number
        resident.save(update_fields=["email", "contact_number", "updated_at"])

    serializer = ResidentSerializer(resident)

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AccountDeletionRateThrottle])
def delete_account_api(request):
    """Reauthenticate and irreversibly remove a resident's login and PII.

    Operational appointment history remains linked to an anonymized resident
    record so barangay queue and audit reports retain their integrity.
    """
    method = str(request.data.get("method", "")).strip().lower()
    credential = str(request.data.get("credential", ""))
    if method not in ("password", "pin"):
        return Response(
            {"success": False, "message": "Choose password or PIN verification."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        resident = request.user.resident_profile
    except Resident.DoesNotExist:
        return Response(
            {"success": False, "message": "Only resident accounts can be deleted here."},
            status=status.HTTP_403_FORBIDDEN,
        )

    verified = request.user.check_password(credential) if method == "password" else (
        credential.isdigit()
        and len(credential) == 4
        and bool(resident.pin_hash)
        and check_password(credential, resident.pin_hash)
    )
    if not verified:
        label = "password" if method == "password" else "PIN"
        return Response(
            {"success": False, "message": f"The {label} you entered is incorrect."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tombstone = uuid.uuid4().hex
    try:
        with transaction.atomic():
            resident = Resident.objects.select_for_update().select_related("user").get(pk=resident.pk)
            user = resident.user

            # Device registrations and resident-facing messages have no audit
            # value once the owner is gone. Appointments and queue records do.
            resident.push_devices.all().delete()
            resident.notifications.all().delete()

            resident.first_name = "Deleted"
            resident.middle_name = ""
            resident.last_name = "Resident"
            resident.suffix = ""
            resident.birthdate = date(1900, 1, 1)
            resident.email = None
            resident.contact_number = f"del{tombstone[:12]}"
            resident.province = ""
            resident.municipality = ""
            resident.pin_hash = ""
            resident.security_setup_stage = Resident.SecuritySetupStage.PASSWORD
            resident.save()

            user.username = f"deleted-{tombstone}"
            user.first_name = ""
            user.last_name = ""
            user.email = ""
            user.is_active = False
            user.set_unusable_password()
            user.save()
    except (DatabaseError, IntegrityError):
        logger.exception("Resident account deletion failed", extra={"resident_id": resident.pk})
        return Response(
            {"success": False, "message": "Your account could not be deleted. No changes were made."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"success": True, "message": "Your account has been successfully deleted."})

@api_view(["POST"])
def register_api(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        resident = serializer.save()
        refresh = RefreshToken.for_user(resident.user)

        return Response(
            {
                "success": True,
                "message": "Account created successfully.",
                "username": resident.user.username,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "security_setup_stage": resident.security_setup_stage,
                "resident": ResidentSerializer(resident).data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "success": False,
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )

@api_view(["GET"])
def barangay_list_api(request):
    barangays = Barangay.objects.filter(is_active=True).order_by("name")

    serializer = BarangaySerializer(barangays, many=True)

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    """Allow a signed-in resident to optionally replace the generated password."""
    current_password = request.data.get("current_password", "")
    new_password = request.data.get("new_password", "")
    confirm_password = request.data.get("confirm_password", "")

    if not request.user.check_password(current_password):
        return Response({"success": False, "message": "Your current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    if new_password != confirm_password:
        return Response({"success": False, "message": "The new passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new_password, request.user)
    except ValidationError as error:
        return Response({"success": False, "message": " ".join(error.messages)}, status=status.HTTP_400_BAD_REQUEST)

    request.user.set_password(new_password)
    request.user.save()
    return Response({"success": True, "message": "Password updated successfully."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_initial_password_api(request):
    """Set the resident's first password during the required setup flow."""
    resident = request.user.resident_profile
    if resident.security_setup_stage != Resident.SecuritySetupStage.PASSWORD:
        return Response({"success": False, "message": "Password setup is not the current security step."}, status=status.HTTP_409_CONFLICT)
    new_password = request.data.get("new_password", "")
    confirm_password = request.data.get("confirm_password", "")
    if new_password != confirm_password:
        return Response({"success": False, "message": "The new passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new_password, request.user)
    except ValidationError as error:
        return Response({"success": False, "message": " ".join(error.messages)}, status=status.HTTP_400_BAD_REQUEST)
    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    resident.security_setup_stage = Resident.SecuritySetupStage.PIN
    resident.save(update_fields=["security_setup_stage", "updated_at"])
    return Response({"success": True, "message": "Your password has been set successfully.", "next_step": resident.security_setup_stage})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_security_pin_api(request):
    resident = request.user.resident_profile
    if resident.security_setup_stage != Resident.SecuritySetupStage.PIN:
        return Response({"success": False, "message": "PIN setup is not the current security step."}, status=status.HTTP_409_CONFLICT)
    pin = str(request.data.get("pin", ""))
    if not pin.isdigit() or len(pin) != 4:
        return Response({"success": False, "message": "Enter exactly four digits."}, status=status.HTTP_400_BAD_REQUEST)
    resident.pin_hash = make_password(pin)
    resident.security_setup_stage = Resident.SecuritySetupStage.FINGERPRINT
    resident.save(update_fields=["pin_hash", "security_setup_stage", "updated_at"])
    return Response({"success": True, "next_step": resident.security_setup_stage})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_security_pin_api(request):
    """Verify the resident's PIN before allowing a sensitive local-device action."""
    resident = request.user.resident_profile
    pin = str(request.data.get("pin", ""))
    if not pin.isdigit() or len(pin) != 4:
        return Response({"success": False, "message": "Enter exactly four digits."}, status=status.HTTP_400_BAD_REQUEST)
    if not resident.pin_hash or not check_password(pin, resident.pin_hash):
        return Response({"success": False, "message": "The PIN you entered is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"success": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_account_password_api(request):
    if not request.user.check_password(request.data.get("password", "")):
        return Response({"success": False, "message": "Your account password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"success": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_security_pin_api(request):
    """Replace a resident PIN only after account-password verification."""
    resident = request.user.resident_profile
    password = request.data.get("password", "")
    new_pin = str(request.data.get("new_pin", ""))
    confirm_pin = str(request.data.get("confirm_pin", ""))
    if not request.user.check_password(password):
        return Response({"success": False, "message": "Your account password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    if not new_pin.isdigit() or len(new_pin) != 4:
        return Response({"success": False, "message": "The new PIN must contain exactly four numeric digits."}, status=status.HTTP_400_BAD_REQUEST)
    if new_pin != confirm_pin:
        return Response({"success": False, "message": "The new PINs do not match."}, status=status.HTTP_400_BAD_REQUEST)
    resident.pin_hash = make_password(new_pin)
    resident.save(update_fields=["pin_hash", "updated_at"])
    return Response({"success": True, "message": "Your 4-digit PIN has been changed successfully."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def advance_security_setup_api(request):
    resident = request.user.resident_profile
    step = request.data.get("step")
    expected = resident.security_setup_stage
    if step != expected or step not in (Resident.SecuritySetupStage.FINGERPRINT, Resident.SecuritySetupStage.FACE):
        return Response({"success": False, "message": "Complete the current security step first."}, status=status.HTTP_409_CONFLICT)
    resident.security_setup_stage = Resident.SecuritySetupStage.FACE if step == Resident.SecuritySetupStage.FINGERPRINT else Resident.SecuritySetupStage.COMPLETE
    resident.save(update_fields=["security_setup_stage", "updated_at"])
    return Response({"success": True, "next_step": resident.security_setup_stage})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def appointments_api(request):
    """Return mobile booking choices or create an appointment."""
    resident = request.user.resident_profile
    ensure_default_time_slots(resident.barangay)
    now = timezone.now()
    today = timezone.localdate()
    services = Service.objects.filter(is_active=True).filter(
        Q(is_temporary=False) |
        Q(is_temporary=True, barangay=resident.barangay, lifecycle=Service.Lifecycle.SCHEDULED,
          event_end_date__gte=today)
    ).annotate(
        live_booking_count=Count(
            "appointments",
            filter=~Q(appointments__status=Appointment.Status.CANCELLED),
        )
    ).order_by("name")
    time_slots = list(TimeSlot.objects.filter(
        barangay=resident.barangay,
        is_active=True,
    ).order_by("start_time"))
    time_slots_by_id = {slot.pk: slot for slot in time_slots}
    slot_capacities = regular_slot_capacities(resident.barangay, time_slots)
    service_configurations = {
        item.service_id: item
        for item in BarangayServiceConfiguration.objects.filter(
            barangay=resident.barangay,
            service__is_temporary=False,
        )
    }

    availability_date = None
    requested_date = request.query_params.get("appointment_date")
    if requested_date:
        try:
            availability_date = date.fromisoformat(requested_date)
        except ValueError:
            return Response({"message": "Please provide a valid appointment date."}, status=status.HTTP_400_BAD_REQUEST)

    occupied_by_slot = {}
    closed_date = None
    if availability_date:
        closed_date = ClosedAppointmentDate.objects.filter(
            barangay=resident.barangay,
            date=availability_date,
        ).first()
        occupied_by_slot = {
            row["time_slot_id"]: row["count"]
            for row in Appointment.objects.filter(
                barangay=resident.barangay,
                appointment_date=availability_date,
                time_slot__isnull=False,
                service__is_temporary=False,
            ).exclude(status=Appointment.Status.CANCELLED)
            .values("time_slot_id")
            .annotate(count=Count("id"))
        }

    def serialize_time_slot(slot):
        booked = occupied_by_slot.get(slot.pk, 0)
        capacity = slot_capacities.get(slot.pk, 0)
        daily_booked = sum(occupied_by_slot.values())
        is_past = availability_date is not None and availability_date < today
        cutoff_passed = (
            availability_date == today
            and timezone.localtime(now).time() >= slot.start_time
        )
        is_full = booked >= capacity
        day_is_full = daily_booked >= regular_daily_capacity(resident.barangay)
        is_available = availability_date is None or not (
            is_past or cutoff_passed or is_full or day_is_full or closed_date
        )
        time_label = f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}"
        if availability_date:
            availability_label = (
                "Unavailable"
                if closed_date or is_past or cutoff_passed
                else "Fully Booked"
                if is_full or day_is_full
                else "Available"
            )
            time_label = f"{time_label} · {booked}/{capacity} – {availability_label}"
        return {
            "id": slot.pk,
            "label": time_label,
            "occupied": booked,
            "capacity": capacity,
            "remaining": 0 if day_is_full else max(capacity - booked, 0),
            "is_fully_booked": is_full or day_is_full,
            "is_available": is_available,
            "closure_reason": closed_date.reason if closed_date else None,
        }

    if request.method == "GET":
        temporary_services = [service for service in services if service.is_temporary]
        resident_bookings_by_service = {}
        if temporary_services:
            resident_bookings = EventBooking.objects.filter(
                appointment__resident=resident,
                appointment__service_id__in=[service.pk for service in temporary_services],
            ).exclude(status=EventBooking.Status.CANCELLED).select_related(
                "appointment"
            ).order_by("pk")
            for booking in resident_bookings:
                resident_bookings_by_service.setdefault(
                    booking.appointment.service_id, booking
                )

        service_choices = []
        for service in services:
            configuration = service_configurations.get(service.pk)
            if not service.is_temporary and configuration and not configuration.is_active:
                continue
            if service.is_temporary and not service.accepts_bookings(now, service.live_booking_count):
                continue
            choice = {"id": service.pk, "name": service.name}
            if service.is_temporary:
                choice.update({
                    "is_temporary": True,
                    "event_start_date": service.event_start_date.isoformat(),
                    "event_end_date": service.event_end_date.isoformat(),
                    "booking_start_date": service.booking_start_date.isoformat(),
                    "booking_end_date": service.booking_end_date.isoformat(),
                    "location": service.location,
                    "remaining_capacity": max((service.capacity or 0) - service.live_booking_count, 0),
                })
            service_choices.append(choice)
        temporary_choices = []
        for service in temporary_services:
            service_status = service.computed_status(now, service.live_booking_count)
            if service_status in {"expired", "cancelled", "deactivated", "archived"}:
                continue
            resident_booking = resident_bookings_by_service.get(service.pk)
            temporary_choices.append({
                "id": service.pk,
                "name": service.name,
                "description": service.description,
                "type": service.get_temporary_type_display(),
                "location": service.location,
                "event_start_date": service.event_start_date.isoformat(),
                "event_end_date": service.event_end_date.isoformat(),
                "booking_start_date": service.booking_start_date.isoformat(),
                "booking_end_date": service.booking_end_date.isoformat(),
                "status": service_status,
                "capacity": service.capacity,
                "remaining_capacity": max(service.capacity - service.live_booking_count, 0) if service.capacity else None,
                "can_book": service.accepts_bookings(now, service.live_booking_count),
                "is_event": True,
                "is_special_service": True,
                "is_booked": resident_booking is not None,
                "event_booking_id": resident_booking.pk if resident_booking else None,
                "requirements": [
                    line.strip().lstrip("-â€¢").strip()
                    for line in service.requirements.splitlines()
                    if line.strip().lstrip("-â€¢").strip()
                ],
            })
        priority = {"ending_soon": 0, "active": 1, "fully_booked": 2, "upcoming": 3, "booking_closed": 4}
        temporary_choices.sort(key=lambda item: (priority.get(item["status"], 9), item["event_start_date"]))
        if request.query_params.get("summary") == "1":
            return Response({"services": service_choices, "temporary_services": temporary_choices, "server_time": now.isoformat()})
        return Response({
            "resident": {
                "first_name": resident.first_name,
                "last_name": resident.last_name,
                "middle_name": resident.middle_name,
                "suffix": resident.suffix,
                "birthdate": resident.birthdate.isoformat(),
                "age": resident.age,
                "sex": resident.get_sex_display(),
                "address": f"{resident.barangay.name}, {resident.municipality}, {resident.province}",
                "barangay": resident.barangay.name,
            },
            "services": service_choices,
            "temporary_services": temporary_choices,
            "server_time": now.isoformat(),
            "time_slots": [serialize_time_slot(slot) for slot in time_slots],
        })

    try:
        service = Service.objects.filter(is_active=True).filter(
            Q(is_temporary=False)
            | Q(is_temporary=True, barangay=resident.barangay)
        ).get(pk=request.data.get("service"))
        if service.is_temporary:
            appointment = create_special_service_booking(resident, service)
        else:
            try:
                time_slot_id = int(request.data.get("time_slot"))
            except (TypeError, ValueError):
                raise TimeSlot.DoesNotExist
            time_slot = time_slots_by_id.get(time_slot_id)
            if time_slot is None:
                raise TimeSlot.DoesNotExist
            appointment_date = date.fromisoformat(request.data.get("appointment_date", ""))
            if appointment_date < timezone.localdate():
                raise ValueError("Please choose today or a future appointment date.")
            appointment = create_appointment(
                resident,
                service,
                appointment_date,
                time_slot,
                request.data.get("purpose", "").strip(),
                request.data.get("sitio", "").strip(),
            )
    except (Service.DoesNotExist, TimeSlot.DoesNotExist, TypeError):
        return Response({"message": "Please select a valid service, date, and time slot."}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as error:
        return Response({"message": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    event_booking = getattr(appointment, "event_booking", None)
    appointment_date_display = appointment.appointment_date.strftime("%B %d, %Y") if appointment.appointment_date else ""
    if event_booking and appointment.service.event_end_date != appointment.service.event_start_date:
        appointment_date_display = (
            f"{appointment.service.event_start_date.strftime('%B %d, %Y')} - "
            f"{appointment.service.event_end_date.strftime('%B %d, %Y')}"
        )
    return Response({
        "success": True,
        "message": "Appointment submitted successfully.",
        "id": appointment.pk,
        "appointment_id": f"QQ-{appointment.created_at.year}-{appointment.pk:05d}",
        "queue_number": appointment.queue_number,
        "service": appointment.service.name,
        "appointment_date": appointment_date_display,
        "time_slot": f"{appointment.time_slot.start_time.strftime('%I:%M %p')} - {appointment.time_slot.end_time.strftime('%I:%M %p')}" if appointment.time_slot else "",
        "status": appointment.get_status_display(),
        "is_event": event_booking is not None,
        "event_booking_id": event_booking.pk if event_booking else None,
        "booking_reference": event_booking.booking_reference if event_booking else None,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def queue_status_api(request):
    """Return the resident's active queue or perform a queue action."""
    resident = request.user.resident_profile
    expire_overdue_appointments(barangay=resident.barangay, resident=resident)

    if request.method == "POST":
        try:
            appointment = resident.appointments.get(pk=request.data.get("appointment_id"))
        except (Appointment.DoesNotExist, TypeError, ValueError):
            return Response({"message": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "cancel":
            if appointment.effective_status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
                return Response({"message": "This appointment can no longer be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            if appointment.appointment_date < timezone.localdate():
                return Response({"message": "Past appointments can no longer be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                appointment.status = Appointment.Status.CANCELLED
                appointment.save(update_fields=["status", "updated_at"])
                QueueTicket.objects.filter(appointment=appointment).update(status=QueueTicket.Status.CANCELLED, updated_at=timezone.now())
                EventBooking.objects.filter(appointment=appointment).update(
                    status=EventBooking.Status.CANCELLED, cancelled_at=timezone.now(), updated_at=timezone.now()
                )
                notify_resident(
                    appointment=appointment,
                    notification_type=Notification.NotificationType.APPOINTMENT_CANCELLED,
                    title="Appointment Cancelled",
                    message="Your appointment has been cancelled.",
                    event_key=f"appointment:{appointment.pk}:resident-cancelled",
                )
                notify_barangay_staff(
                    appointment=appointment,
                    title="Appointment Cancelled",
                    message=f"{resident} cancelled {appointment.service.name} ({appointment.queue_number}).",
                    event_key=f"appointment:{appointment.pk}:staff-cancelled",
                )
            return Response({"success": True, "message": "Your appointment has been cancelled."})

        if action == "check_in":
            if appointment.appointment_date != timezone.localdate():
                return Response({"message": "Check-in is only available on your appointment date."}, status=status.HTTP_400_BAD_REQUEST)
            if appointment.service.is_temporary:
                return Response(
                    {"message": "Special Service attendance uses the event check-in process."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                appointment = Appointment.objects.select_for_update(of=("self",)).select_related(
                    "time_slot", "service"
                ).get(pk=appointment.pk, resident=resident)
                ticket = QueueTicket.objects.select_for_update().filter(
                    appointment=appointment
                ).first()
                if not ticket:
                    return Response(
                        {"message": "A valid queue ticket is required before check-in."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if ticket.notes == CHECKED_IN_NOTE:
                    return Response({
                        "success": True,
                        "changed": False,
                        "checked_in": True,
                        "staff_notification_created": False,
                        "message": "You are already checked in.",
                    })
                now = timezone.now()
                if is_appointment_expired(appointment, at=now, ticket=ticket):
                    appointment.status = Appointment.Status.MISSED
                    appointment.save(update_fields=["status", "updated_at"])
                    ticket.status = QueueTicket.Status.MISSED
                    ticket.save(update_fields=["status", "updated_at"])
                    return Response(
                        {"message": "This appointment has expired and can no longer be checked in."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                start_at = appointment_start_at(appointment)
                end_at = appointment_expiration_at(appointment)
                if start_at is None or end_at is None or now < start_at:
                    return Response(
                        {"message": "Check-in is available only during your scheduled time slot."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not appointment_checkin_window_open(appointment, at=now):
                    return Response(
                        {"message": "This appointment has expired and can no longer be checked in."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if appointment.status != Appointment.Status.CONFIRMED or ticket.status != QueueTicket.Status.WAITING:
                    return Response(
                        {"message": "This appointment is not eligible for check-in."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                ticket.notes = CHECKED_IN_NOTE
                ticket.save(update_fields=["notes", "updated_at"])
                staff_notifications = notify_barangay_staff(
                    appointment=appointment,
                    title="Resident Checked In",
                    message=(f"{resident} has successfully checked in for {appointment.service.name}. "
                             f"Queue Number: {appointment.queue_number}."),
                    event_key=f"appointment:{appointment.pk}:staff-check-in",
                )
            return Response({
                "success": True,
                "changed": True,
                "checked_in": True,
                "staff_notification_created": bool(staff_notifications),
                "message": (
                    "You have successfully checked in for your appointment. Barangay staff "
                    "have been notified. Please wait for your queue number to be called."
                ),
            })

        return Response({"message": "Invalid queue action."}, status=status.HTTP_400_BAD_REQUEST)

    appointment = resident.appointments.select_related("service", "barangay", "time_slot", "queue_ticket").exclude(
        service__is_temporary=True,
    ).exclude(
        queue_ticket__claim_status=QueueTicket.ClaimStatus.CLAIMED,
    ).filter(
        appointment_date__gte=timezone.localdate(),
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED, Appointment.Status.ONGOING],
    ).order_by("appointment_date", "time_slot__start_time").first()
    if not appointment:
        return Response({"appointment": None})
    try:
        resident_ticket = appointment.queue_ticket
    except QueueTicket.DoesNotExist:
        resident_ticket = None

    queue = QueueTicket.objects.filter(
        live_queue_participation_q(),
        appointment__appointment_date=appointment.appointment_date,
        appointment__barangay=appointment.barangay,
        appointment__service=appointment.service,
    ).select_related("appointment")
    now_serving = queue.filter(status=QueueTicket.Status.NOW_SERVING).first()
    people_ahead = queue.filter(
        status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.NOW_SERVING],
        appointment__queue_number__lt=appointment.queue_number,
    ).count()
    fee = appointment.service_fee_snapshot
    if fee is None:
        fee = effective_service_fee(appointment.barangay, appointment.service)
    service_fee = "Free" if fee == 0 else f"₱{fee:,.2f}"
    middle_initial = f" {resident.middle_name[0].upper()}." if resident.middle_name else ""
    suffix = f" {resident.suffix}" if resident.suffix else ""
    return Response({
        "appointment": {
            "id": appointment.pk,
            "appointment_id": f"QQ-{appointment.created_at.year}-{appointment.pk:05d}",
            "name": f"{resident.first_name}{middle_initial} {resident.last_name}{suffix}",
            "service": appointment.service.name,
            "service_fee": service_fee,
            "date": appointment.appointment_date.strftime("%B %d, %Y"),
            "time_slot": f"{appointment.time_slot.start_time.strftime('%I:%M %p')} - {appointment.time_slot.end_time.strftime('%I:%M %p')}",
            "barangay": appointment.barangay.name,
            "queue_number": appointment.queue_number,
            "status": appointment.workflow_status_display,
            "status_code": appointment.status,
            "checked_in": bool(resident_ticket and resident_ticket.notes == CHECKED_IN_NOTE),
            "now_serving": now_serving.queue_number if now_serving else "—",
            "people_ahead": people_ahead,
            "estimated_wait": people_ahead * effective_service_duration(
                appointment.barangay, appointment.service
            ),
        }
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def transactions_api(request):
    """List and manage the signed-in resident's appointment history."""
    resident = request.user.resident_profile
    expire_overdue_appointments(barangay=resident.barangay, resident=resident)

    if request.method == "POST":
        try:
            appointment = resident.appointments.get(pk=request.data.get("appointment_id"))
        except (Appointment.DoesNotExist, TypeError, ValueError):
            return Response({"message": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "cancel":
            if appointment.effective_status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
                return Response({"message": "This appointment can no longer be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            if appointment.appointment_date < timezone.localdate():
                return Response({"message": "Past appointments can no longer be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                appointment.status = Appointment.Status.CANCELLED
                appointment.save(update_fields=["status", "updated_at"])
                QueueTicket.objects.filter(appointment=appointment).update(status=QueueTicket.Status.CANCELLED, updated_at=timezone.now())
                notify_resident(
                    appointment=appointment,
                    notification_type=Notification.NotificationType.APPOINTMENT_CANCELLED,
                    title="Appointment Cancelled",
                    message="Your appointment has been cancelled.",
                    event_key=f"appointment:{appointment.pk}:resident-cancelled",
                )
                notify_barangay_staff(
                    appointment=appointment,
                    title="Appointment Cancelled",
                    message=f"{resident} cancelled {appointment.service.name} ({appointment.queue_number}).",
                    event_key=f"appointment:{appointment.pk}:staff-cancelled",
                )
            return Response({"success": True, "message": "Appointment cancelled."})

        if action == "delete":
            if hasattr(appointment, "event_booking"):
                return Response({"message": "Event registration records are retained as booking history."}, status=status.HTTP_400_BAD_REQUEST)
            if appointment.status not in (Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.MISSED):
                return Response({"message": "Only completed, cancelled, or expired appointments can be deleted."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                with transaction.atomic():
                    # Delete owned dependents explicitly so this action also works
                    # against databases created before all cascade rules were aligned.
                    notification_ids = Notification.objects.filter(appointment=appointment).values_list("pk", flat=True)
                    PushDelivery.objects.filter(notification_id__in=notification_ids).delete()
                    Notification.objects.filter(appointment=appointment).delete()
                    ticket_ids = QueueTicket.objects.filter(appointment=appointment).values_list("pk", flat=True)
                    GeneratedDocument.objects.filter(ticket_id__in=ticket_ids).delete()
                    QueueTicket.objects.filter(appointment=appointment).delete()
                    appointment.delete()
            except (ProtectedError, IntegrityError, DatabaseError):
                return Response(
                    {"message": "This transaction could not be deleted because a related record is still in use. Please try again shortly."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response({"success": True, "message": "Appointment deleted from your history."})

        return Response({"message": "Invalid transaction action."}, status=status.HTTP_400_BAD_REQUEST)

    appointments_queryset = resident.appointments.select_related(
        "service", "barangay", "time_slot", "queue_ticket", "event_booking"
    ).order_by("-appointment_date", "-created_at", "-pk")

    # Temporary compatibility bridge: clients must explicitly opt in to the
    # paginated contract. Installed legacy clients expect the complete history
    # and perform their search and status filtering locally.
    use_pagination = request.query_params.get("paginate") == "1"
    page = None
    paginator = None
    if use_pagination:
        status_filter = request.query_params.get("status", "all").strip().lower()
        if status_filter == "pending":
            appointments_queryset = appointments_queryset.filter(
                status__in=[
                    Appointment.Status.PENDING,
                    Appointment.Status.CONFIRMED,
                    Appointment.Status.ONGOING,
                ],
            ).filter(
                Q(event_booking__isnull=False)
                | ~Q(queue_ticket__claim_status=QueueTicket.ClaimStatus.CLAIMED)
            )
        elif status_filter == "completed":
            appointments_queryset = appointments_queryset.filter(
                Q(status=Appointment.Status.COMPLETED)
                | Q(
                    event_booking__isnull=True,
                    queue_ticket__claim_status=QueueTicket.ClaimStatus.CLAIMED,
                )
            )
        elif status_filter == "cancelled":
            appointments_queryset = appointments_queryset.filter(
                status=Appointment.Status.CANCELLED
            )
        elif status_filter == "expired":
            appointments_queryset = appointments_queryset.filter(
                status=Appointment.Status.MISSED
            )
        elif status_filter != "all":
            return Response(
                {"message": "Invalid transaction status filter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        search = request.query_params.get("q", "").strip()
        if search:
            appointments_queryset = appointments_queryset.annotate(
                transaction_reference=Concat(
                    Value("QQ-"),
                    Cast(ExtractYear("created_at"), output_field=CharField()),
                    Value("-"),
                    LPad(Cast("pk", output_field=CharField()), 5, Value("0")),
                    output_field=CharField(),
                )
            ).filter(
                Q(service__name__icontains=search)
                | Q(queue_number__icontains=search)
                | Q(transaction_reference__icontains=search)
            )

        paginator = TransactionsPagination()
        appointments = list(paginator.paginate_queryset(appointments_queryset, request))
        page = paginator.page
        assert page is not None
    else:
        appointments = list(appointments_queryset)
    legacy_fee_keys = {
        (appointment.barangay_id, appointment.service_id)
        for appointment in appointments
        if appointment.service_fee_snapshot is None
    }
    configured_fees = {
        (configuration.barangay_id, configuration.service_id): configuration.fee
        for configuration in BarangayServiceConfiguration.objects.filter(
            barangay_id__in={key[0] for key in legacy_fee_keys},
            service_id__in={key[1] for key in legacy_fee_keys},
        )
    } if legacy_fee_keys else {}
    records = []
    now = timezone.now()
    for appointment in appointments:
        try:
            ticket = appointment.queue_ticket
        except QueueTicket.DoesNotExist:
            ticket = None
        event_booking = getattr(appointment, "event_booking", None)
        event_status = None
        if event_booking:
            event_status = event_booking.status
            if appointment.service.event_end_date and timezone.localdate(now) > appointment.service.event_end_date and event_status == EventBooking.Status.CONFIRMED:
                event_status = "event_ended"
            if appointment.service.lifecycle == Service.Lifecycle.CANCELLED:
                event_status = EventBooking.Status.CANCELLED
        fee = appointment.service_fee_snapshot
        if fee is None:
            fee = configured_fees.get(
                (appointment.barangay_id, appointment.service_id),
                Decimal("0.00"),
            )
        records.append({
            "id": appointment.pk,
            "appointment_id": f"QQ-{appointment.created_at.year}-{appointment.pk:05d}",
            "service": appointment.service.name,
            "service_fee": "Free" if fee == 0 else f"₱{fee:,.2f}",
            "status": appointment.workflow_status_display,
            "status_code": (
                appointment.status if event_booking else appointment.effective_status
            ),
            "date_booked": appointment.created_at.strftime("%B %d, %Y"),
            "appointment_date": appointment.appointment_date.strftime("%B %d, %Y") if appointment.appointment_date else "",
            "date_claimed": ticket.claimed_at.strftime("%B %d, %Y") if ticket and ticket.claimed_at else None,
            "time_slot": f"{appointment.time_slot.start_time.strftime('%I:%M %p')} - {appointment.time_slot.end_time.strftime('%I:%M %p')}" if appointment.time_slot else "",
            "barangay": appointment.barangay.name,
            "queue_number": appointment.queue_number,
            "is_event": event_booking is not None,
            "event_booking_id": event_booking.pk if event_booking else None,
            "booking_reference": event_booking.booking_reference if event_booking else None,
            "event_booking_status": event_status,
        })
    response_data = {"transactions": records}
    if page is not None and paginator is not None:
        response_data["pagination"] = {
            "count": page.paginator.count,
            "page": page.number,
            "page_size": paginator.get_page_size(request),
            "total_pages": page.paginator.num_pages,
            "next_page": page.next_page_number() if page.has_next() else None,
            "previous_page": page.previous_page_number() if page.has_previous() else None,
        }
    return Response(response_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def event_booking_pass_api(request, pk):
    resident = request.user.resident_profile
    try:
        booking = EventBooking.objects.select_related(
            "appointment__service", "appointment__resident", "appointment__time_slot"
        ).get(pk=pk, appointment__resident=resident)
    except EventBooking.DoesNotExist:
        return Response({"message": "Event booking not found."}, status=status.HTTP_404_NOT_FOUND)
    appointment, event = booking.appointment, booking.appointment.service
    now = timezone.now()
    if booking.status == EventBooking.Status.CANCELLED or event.lifecycle == Service.Lifecycle.CANCELLED or appointment.status == Appointment.Status.CANCELLED:
        display_status, can_check_in = "cancelled", False
    elif event.event_end_date and timezone.localdate(now) > event.event_end_date:
        display_status, can_check_in = "event_ended", False
    elif booking.status == EventBooking.Status.CHECKED_IN:
        display_status, can_check_in = "checked_in", False
    else:
        display_status, can_check_in = "confirmed", True
    resident_name = " ".join(filter(None, [appointment.resident.first_name, appointment.resident.middle_name, appointment.resident.last_name, appointment.resident.suffix]))
    return Response({
        "id": booking.pk,
        "booking_reference": booking.booking_reference,
        "qr_token": booking.qr_token(),
        "status": display_status,
        "can_check_in": can_check_in,
        "checked_in_at": booking.checked_in_at.isoformat() if booking.checked_in_at else None,
        "resident_name": resident_name,
        "event_name": event.name,
        "event_date": (
            event.event_start_date.strftime("%B %d, %Y")
            if event.event_start_date == event.event_end_date
            else f"{event.event_start_date.strftime('%B %d, %Y')} - {event.event_end_date.strftime('%B %d, %Y')}"
        ),
        "location": event.location,
        "requirements": [
            line.strip().lstrip("-â€¢").strip()
            for line in event.requirements.splitlines()
            if line.strip().lstrip("-â€¢").strip()
        ],
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def notifications_api(request):
    """List resident notifications and allow them to be marked as read."""
    resident = request.user.resident_profile

    if request.method == "POST":
        owned_notifications = Notification.objects.filter(
            recipient=request.user,
            recipient_role=Notification.RecipientRole.RESIDENT,
        )
        notification_id = request.data.get("notification_id")
        if notification_id:
            updated = owned_notifications.filter(pk=notification_id).update(is_read=True)
            if not updated:
                return Response({"message": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            owned_notifications.filter(is_read=False).update(is_read=True)
        return Response({"success": True})

    notifications = Notification.objects.filter(
        recipient=request.user,
        recipient_role=Notification.RecipientRole.RESIDENT,
    ).order_by("-created_at")
    unread_count = notifications.filter(is_read=False).count()
    if request.query_params.get("summary") == "1":
        return Response({"unread_count": unread_count})
    page_value = request.query_params.get("page")
    if page_value:
        try:
            page = max(1, int(page_value))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 50))))
        except (TypeError, ValueError):
            return Response({"message": "Invalid pagination parameters."}, status=status.HTTP_400_BAD_REQUEST)
        total = notifications.count()
        start = (page - 1) * page_size
        notifications = notifications[start:start + page_size]
        pagination = {"page": page, "page_size": page_size, "total": total, "has_more": start + page_size < total}
    else:
        pagination = None
    return Response({
        "unread_count": unread_count,
        "notifications": [{
            "id": item.pk,
            "type": item.notification_type,
            "title": item.title,
            "message": item.message,
            "is_read": item.is_read,
            "appointment_id": item.appointment_id,
            "created_at": item.created_at.isoformat(),
        } for item in notifications],
        **({"pagination": pagination} if pagination else {}),
    })


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def push_devices_api(request):
    """Register, inspect, or deactivate only the signed-in resident's device."""
    resident = request.user.resident_profile
    if request.method == "GET":
        return Response({"enabled": resident.push_devices.filter(is_active=True).exists()})

    token = str(request.data.get("token", "")).strip()
    if not token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
        return Response({"message": "A valid Expo push token is required."}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        resident.push_devices.filter(expo_push_token=token).update(is_active=False, updated_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)

    # A token belongs to one account at a time; account switches cannot leak notifications.
    device, _ = PushDevice.objects.update_or_create(
        expo_push_token=token,
        defaults={
            "resident": resident,
            "platform": str(request.data.get("platform", ""))[:20],
            "device_name": str(request.data.get("device_name", ""))[:120],
            "is_active": True,
        },
    )
    return Response({"success": True, "device_id": device.pk})


def _chat_database_context(resident, message=""):
    """Build a minimal context from authenticated, resident-scoped records."""
    data = assistant_data_for(resident, message)
    sections = [f"Resident barangay: {resident.barangay.name}"]

    if "office" in data.intents:
        sections.append(f"QuickQueue office hours: {office_hours()}")

    if "services" in data.intents:
        lines = []
        for service in data.services:
            configuration = data.service_configurations.get(service.pk)
            duration = configuration.estimated_duration if configuration else service.estimated_duration
            detail = (
                f"- {service.name}: description={service.description.strip() or 'not recorded'}; "
                f"requirements={service.requirements.strip() or 'not recorded'}; "
                f"fee={money_label(service_fee_for(service, data.service_configurations))}; "
                f"estimated processing duration={duration} minutes"
            )
            if service.is_temporary:
                detail += (
                    f"; type={service.get_temporary_type_display()}; location={service.location or 'not recorded'}; "
                    f"event dates={service.event_start_date or 'not recorded'} to {service.event_end_date or 'not recorded'}; "
                    f"booking status={service.computed_status()}"
                )
            lines.append(detail)
        sections.extend(["Available services for this barangay:", *(lines or ["- No active services are recorded."])])

    if data.intents & {"appointments", "queue", "documents"}:
        appointment_lines = []
        for index, appointment in enumerate(data.active_appointments):
            snapshot = queue_snapshot_for(appointment, data.service_configurations)
            prefix = (
                f"Active appointment: ID QQ-{appointment.created_at.year}-{appointment.pk:05d}; "
                if index == 0 else "- Other active booking: "
            )
            appointment_lines.append(
                f"{prefix}service={appointment.service.name}; "
                f"date={appointment.appointment_date.isoformat() if appointment.appointment_date else 'Date not assigned'}; "
                f"time={appointment.time_slot.start_time.strftime('%I:%M %p') + '-' + appointment.time_slot.end_time.strftime('%I:%M %p') if appointment.time_slot else 'Time not assigned'}; "
                f"status={appointment.get_status_display()}; queue number={snapshot.queue_number or 'not assigned'}; "
                f"queue status={snapshot.status}; now serving={snapshot.now_serving or 'not recorded'}; "
                f"people ahead={snapshot.people_ahead}; estimated wait={snapshot.estimated_wait_minutes} minutes"
            )
        sections.extend(appointment_lines or ["Active appointment: none in the resident's QuickQueue record."])

    if data.transactions:
        transaction_lines = []
        for appointment in data.transactions:
            snapshot = queue_snapshot_for(appointment, data.service_configurations)
            transaction_lines.append(
                f"- ID QQ-{appointment.created_at.year}-{appointment.pk:05d}; service={appointment.service.name}; "
                f"appointment status={appointment.get_status_display()}; date={appointment.appointment_date or 'not assigned'}; "
                f"queue status={snapshot.status}; document claim status={snapshot.claim_status or 'not recorded'}; "
                f"document file available={'yes' if snapshot.document_available else 'no'}; "
                f"additional document requirements={snapshot.requirements or 'none recorded'}"
            )
        sections.extend(["Resident transactions and document status:", *transaction_lines])

    if "events" in data.intents:
        event_lines = [
            f"- {event.name}: location={event.location or 'not recorded'}; dates={event.event_start_date or 'not recorded'} to "
            f"{event.event_end_date or 'not recorded'}; requirements={event.requirements.strip() or 'not recorded'}; "
            f"booking status={event.computed_status()}"
            for event in data.events
        ]
        registration_lines = [
            f"- {booking.appointment.service.name}: booking reference={booking.booking_reference}; "
            f"registration status={booking.get_status_display()}"
            for booking in data.event_registrations
        ]
        sections.extend(["Events and temporary services for this barangay:", *(event_lines or ["- None recorded."])])
        sections.extend(["Resident event registrations:", *(registration_lines or ["- None recorded."])])

    if "notifications" in data.intents:
        sections.extend([
            "Resident recent notifications:",
            *([f"- {item.title}: {item.message}" for item in data.notifications] or ["- None recorded."]),
        ])

    if "knowledge" in data.intents:
        sections.extend([
            "Approved QuickQueue knowledge:",
            *([f"- {item.title}: {item.content}" for item in data.knowledge] or ["- None recorded."]),
        ])

    sections.append("Any fact absent or marked not recorded must not be guessed.")
    return "\n".join(sections), data.primary_appointment, list(data.active_appointments), data


def _built_in_chat_reply(message, resident, appointment, data=None):
    """Provide safe QuickQueue guidance when the external AI provider is unavailable."""
    text = message.lower()
    data = data or assistant_data_for(resident, message)
    services = list(data.services)
    appointment_topic = any(word in text for word in (
        "appointment", "queue", "check in", "check-in", "track", "status", "number", "wait", "cancel"
    ))
    if appointment is None and appointment_topic and "book" not in text:
        return (
            "You don’t have any appointments at the moment. To book one:\n\n"
            "1. Open the Book tab.\n\n"
            "2. Select the service you need.\n\n"
            "3. Choose an available date and time.\n\n"
            "4. Review the details and submit."
        )
    if "book" in text or "appointment" in text and appointment is None:
        return (
            "To book an appointment:\n\n"
            "1. Open the Book tab.\n\n"
            "2. Select a barangay service.\n\n"
            "3. Choose an available date and time.\n\n"
            "4. Complete and review the details, then submit.\n\n"
            "After booking, view it in Queue or Transactions."
        )
    if "check in" in text or "check-in" in text:
        if appointment.appointment_date is None:
            return (
                "According to your QuickQueue record, your appointment date and time have not "
                "been assigned yet. Please check Queue or contact barangay staff before checking in."
            )
        if appointment.appointment_date != timezone.localdate():
            return (
                f"According to your QuickQueue record, check-in is available on "
                f"{appointment.appointment_date.strftime('%B %d, %Y')}. On that date, open Queue, "
                "find Appointment Actions, and tap Check In."
            )
        return "Open the Queue tab, find Appointment Actions, and tap Check In. Wait for QuickQueue to confirm that staff were notified."
    if "cancel" in text:
        if (appointment.status in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED)
                and (appointment.appointment_date is None or appointment.appointment_date >= timezone.localdate())):
            return "You can cancel this appointment from the Queue or Transactions tab. Open the appointment, tap Cancel Appointment, and confirm."
        return f"According to your QuickQueue record, this appointment is {appointment.get_status_display()} and can no longer be cancelled in the app. Contact barangay staff if you need help."
    if any(word in text for word in ("queue", "number", "wait", "status", "track")):
        if hasattr(appointment, "event_booking"):
            return (
                f"According to your QuickQueue record, {appointment.service.name} is an event booking, "
                f"so it uses booking reference {appointment.event_booking.booking_reference} and a QR pass "
                "instead of the regular appointment queue."
            )
        ticket = QueueTicket.objects.filter(appointment=appointment).first()
        queue_number = (ticket.queue_number if ticket else appointment.queue_number or "").strip()
        date_text = appointment.appointment_date.strftime("%B %d, %Y") if appointment.appointment_date else None
        subject = f"Your {appointment.service.name} appointment"
        if date_text:
            subject += f" on {date_text}"
        if not queue_number:
            return (
                f"{subject} is {appointment.get_status_display().lower()}, but a queue number hasn't been assigned yet. "
                "You can check the Queue tab for updates once it becomes available."
            )
        queue_status = ticket.get_status_display() if ticket else None
        status_sentence = f" Your current queue status is {queue_status}." if queue_status else ""
        return (
            f"Your queue number for your {appointment.service.name} appointment"
            f"{f' on {date_text}' if date_text else ''} is {queue_number}. "
            f"Your appointment is {appointment.get_status_display().lower()}.{status_sentence} "
            "You can monitor updates through the Queue tab."
        )
    if "notification" in text:
        return "Open Notifications to read the latest update. Use Queue when the notification requires a queue action, or Transactions to review the appointment details."
    if "office hour" in text or "opening hour" in text or "when are you open" in text:
        return f"The office hours shown in QuickQueue are {office_hours()}"
    if any(word in text for word in ("document", "processing", "pickup", "pick up", "claim", "ready")):
        if not data.transactions:
            return "You do not have a document transaction recorded in QuickQueue."
        transaction = data.transactions[0]
        snapshot = queue_snapshot_for(transaction, data.service_configurations)
        if snapshot.claim_status:
            detail = f"According to your QuickQueue record, the document status for {transaction.service.name} is {snapshot.claim_status}."
            if snapshot.requirements:
                detail += f" Additional requirements: {snapshot.requirements}."
            return detail
        return f"QuickQueue does not currently list a document pickup status for your {transaction.service.name} transaction."
    if any(word in text for word in ("event", "special service", "temporary service", "registration", "qr pass", "booking reference")):
        if data.event_registrations:
            registration = data.event_registrations[0]
            return (
                f"According to your QuickQueue record, your registration for {registration.appointment.service.name} "
                f"is {registration.get_status_display()} with booking reference {registration.booking_reference}."
            )
        if data.events:
            names = ", ".join(event.name for event in data.events)
            return f"The events and temporary services available for your barangay are: {names}."
        return "QuickQueue does not currently list an event or temporary service for your barangay."
    if "requirement" in text or "clearance" in text:
        matching_service = _match_service_from_message(text, services)
        if matching_service:
            requirements = matching_service.requirements.strip()
            if requirements:
                return f"According to QuickQueue, the requirements for {matching_service.name} are: {requirements}"
            return f"QuickQueue does not currently list requirements for {matching_service.name}. Please confirm them with {resident.barangay.name} barangay staff."
        names = ", ".join(service.name for service in services)
        if names:
            return f"Which service do you need requirements for? The active services in QuickQueue are: {names}."
        return "QuickQueue does not currently list any active services. Please contact barangay staff for assistance."
    if any(word in text for word in ("fee", "cost", "price")):
        matching_service = _match_service_from_message(text, services)
        if matching_service:
            fee = service_fee_for(matching_service, data.service_configurations)
            return f"According to QuickQueue, the fee for {matching_service.name} is {money_label(fee)}."
        return "Which service fee would you like to check?"
    if "service" in text or "available" in text:
        names = ", ".join(service.name for service in services)
        if names:
            return f"The active services available in QuickQueue are: {names}. Open the Book tab to select one and view its details."
        return "QuickQueue does not currently list any active services. Please contact barangay staff for assistance."
    return "I can help with booking, check-in, queue status, appointment tracking, notifications, and using the QuickQueue app."


def _match_service_from_message(message, services):
    """Match an active service despite minor spelling errors in a resident's message."""
    message_tokens = re.findall(r"[a-z0-9]+", message.lower())
    ignored_tokens = {"a", "an", "for", "of", "the", "to"}
    best_service = None
    best_score = 0.0

    for service in services:
        service_tokens = [
            token for token in re.findall(r"[a-z0-9]+", service.name.lower())
            if token not in ignored_tokens
        ]
        if not service_tokens:
            continue
        matched = sum(
            1 for service_token in service_tokens
            if any(SequenceMatcher(None, service_token, message_token).ratio() >= 0.82 for message_token in message_tokens)
        )
        score = matched / len(service_tokens)
        if score > best_score:
            best_service = service
            best_score = score

    return best_service if best_score >= 0.66 else None


def _format_chat_instructions(reply):
    """Turn inline numbered instructions into a readable vertical list."""
    return re.sub(r"\s+(?=\d+[.)]\s)", "\n\n", reply).strip()


def _record_question_topic(message, unanswered=False):
    """Group close wording variants without treating resident text as knowledge."""
    normalized = " ".join(re.findall(r"[a-z0-9]+", message.lower()))[:500]
    if not normalized:
        return
    topic = ChatQuestionTopic.objects.filter(normalized_question=normalized).first()
    if topic is None:
        for candidate in ChatQuestionTopic.objects.order_by("-last_asked_at")[:100]:
            if SequenceMatcher(None, normalized, candidate.normalized_question).ratio() >= 0.86:
                topic = candidate
                break
    if topic is None:
        ChatQuestionTopic.objects.create(
            normalized_question=normalized,
            example_question=message[:500],
            unanswered_count=int(unanswered),
        )
        return
    ChatQuestionTopic.objects.filter(pk=topic.pk).update(
        count=F("count") + 1,
        unanswered_count=F("unanswered_count") + int(unanswered),
        last_asked_at=timezone.now(),
    )


def _chat_suggestions(message, reply, appointment):
    text = f"{message} {reply}".lower()
    if appointment and hasattr(appointment, "event_booking"):
        candidates = ["What are the event requirements?", "Where is the event?", "How do I use my QR pass?"]
    elif appointment:
        if "called" in text or "now serving" in text:
            candidates = ["What should I do when my number is called?", "What should I bring?", "When is my appointment?"]
        else:
            candidates = ["What is my queue number?", "What should I bring?", "When is my appointment?"]
    else:
        candidates = ["How do I book an appointment?", "What services are available?", "How do I check my booking status?"]
    message_words = set(re.findall(r"[a-z0-9]+", message.lower()))
    filtered = [item for item in candidates if set(re.findall(r"[a-z0-9]+", item.lower())) != message_words]
    return filtered[:3]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_health_api(request):
    """Check authenticated chat dependencies without calling or billing Gemini."""
    started = time.monotonic()
    request_id = _safe_request_id(request)
    close_old_connections()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        logger.error(
            "chat_health request_id=%s status=503 category=database duration_ms=%d",
            request_id, int((time.monotonic() - started) * 1000),
        )
        close_old_connections()
        return Response(
            {"status": "unavailable", "category": "database", "retryable": True},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        check_gemini_ready()
    except GeminiUnavailable as error:
        logger.error(
            "chat_health request_id=%s status=%d category=%s duration_ms=%d",
            request_id, error.http_status, error.code, int((time.monotonic() - started) * 1000),
        )
        return Response(
            {"status": "unavailable", "category": error.code, "retryable": error.retryable},
            status=error.http_status,
        )

    logger.info(
        "chat_health request_id=%s status=200 category=ready duration_ms=%d",
        request_id, int((time.monotonic() - started) * 1000),
    )
    return Response({"status": "ready"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatRateThrottle])
def chat_api(request):
    started = time.monotonic()
    request_id = _safe_request_id(request)
    message = str(request.data.get("message", "")).strip()
    if not message:
        return Response({"message": "Please enter a message."}, status=status.HTTP_400_BAD_REQUEST)
    if len(message) > 500:
        return Response({"message": "Please keep your message under 500 characters."}, status=status.HTTP_400_BAD_REQUEST)

    close_old_connections()
    resident = request.user.resident_profile
    try:
        session_id = request.data.get("session_id")
        session = ChatSession.objects.filter(id=session_id, resident=resident).first() if session_id else None
        if session_id and session is None:
            return Response({"message": "This chat session is not available."}, status=status.HTTP_404_NOT_FOUND)
        session = session or ChatSession.objects.create(resident=resident)
        history = list(session.messages.order_by("-created_at")[:8].values("role", "text"))[::-1]
        ChatMessage.objects.create(session=session, role=ChatMessage.Role.RESIDENT, text=message)
        database_context, appointment, active_appointments, assistant_data = _chat_database_context(resident, message)
    except DatabaseError:
        logger.error(
            "chat_request request_id=%s status=503 category=database location=context duration_ms=%d",
            request_id, int((time.monotonic() - started) * 1000),
        )
        close_old_connections()
        return Response(
            {"message": "QuickQueue is reconnecting to its records. Please retry in a moment.", "error_code": "database_unavailable", "retryable": True},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    language = detect_language(message, history)
    used_ai = False
    ai_error_code = None
    reply = deterministic_reply(message, assistant_data, language, history)
    if reply is None:
        try:
            reply = ask_gemini(message, database_context, history, language.name)
            used_ai = True
        except GeminiUnavailable as error:
            ai_error_code = error.code
            logger.warning("Gemini unavailable; using QuickQueue guidance fallback (%s)", error.code)
            reply = provider_failure_reply(language)
    reply = _format_chat_instructions(reply)
    assistant_message = ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.ASSISTANT, text=reply,
        source="gemini" if used_ai else "verified_backend", error_code=ai_error_code or "",
    )
    _record_question_topic(message, unanswered=bool(ai_error_code))

    logger.info(
        "chat_request request_id=%s status=200 category=%s location=%s duration_ms=%d",
        request_id,
        ai_error_code or "success",
        "gemini" if used_ai or ai_error_code else "verified_backend",
        int((time.monotonic() - started) * 1000),
    )

    provider_failed = ai_error_code is not None
    return Response({
        "reply": reply,
        "suggestions": _chat_suggestions(message, reply, appointment),
        "source": "QuickQueue records and AI guidance" if used_ai else "QuickQueue records and built-in guidance",
        "fallback": provider_failed,
        "service_status": "degraded" if provider_failed else "online",
        "session_id": str(session.id),
        "message_id": assistant_message.pk,
        **({"error_code": ai_error_code} if ai_error_code else {}),
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def chat_session_api(request, session_id):
    deleted, _ = ChatSession.objects.filter(id=session_id, resident=request.user.resident_profile).delete()
    if not deleted:
        return Response({"message": "This chat session is not available."}, status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_feedback_api(request, message_id):
    helpful = request.data.get("helpful")
    if not isinstance(helpful, bool):
        return Response({"message": "Helpful must be true or false."}, status=status.HTTP_400_BAD_REQUEST)
    message = ChatMessage.objects.filter(
        pk=message_id, role=ChatMessage.Role.ASSISTANT,
        session__resident=request.user.resident_profile,
    ).first()
    if not message:
        return Response({"message": "This assistant response is not available."}, status=status.HTTP_404_NOT_FOUND)
    ChatFeedback.objects.update_or_create(
        message=message,
        defaults={"resident": request.user.resident_profile, "helpful": helpful},
    )
    return Response({"saved": True})
