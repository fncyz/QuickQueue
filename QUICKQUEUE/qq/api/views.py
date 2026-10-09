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
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date
from difflib import SequenceMatcher
import re

from qq.models import Appointment, BarangayServiceConfiguration, BarangayStaff, ClosedAppointmentDate, DocumentTemplate, EventBooking, GeneratedDocument, Notification, PushDelivery, PushDevice, QueueTicket, Service, TimeSlot
from qq.services.appointment_service import create_appointment, create_special_service_booking
from qq.services.configuration_service import effective_service_duration, effective_service_fee
from qq.services.timeslot_service import ensure_default_time_slots, regular_daily_capacity, regular_slot_capacity
from qq.gemini_service import GeminiUnavailable, ask_gemini
from .throttles import ChatRateThrottle


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
    template = serializer.save(barangay=barangay, uploaded_by=request.user)
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
        template.template_file.delete(save=False)
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = DocumentTemplateSerializer(template, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    if "template_file" in serializer.validated_data:
        template.version += 1
        template.template_file.delete(save=False)
    template = serializer.save()
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
    fee = appointment.service_fee_snapshot
    if fee is None:
        fee = effective_service_fee(appointment.barangay, appointment.service)
    service_fee = "Free" if fee == 0 else f"₱{fee:,.2f}"
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
    if not (
        len(new_password) >= 8
        and re.search(r"[A-Z]", new_password)
        and re.search(r"[a-z]", new_password)
        and re.search(r"\d", new_password)
        and re.search(r"[^A-Za-z0-9]", new_password)
    ):
        return Response({"success": False, "message": "Use at least 8 characters with uppercase, lowercase, a number, and a special character."}, status=status.HTTP_400_BAD_REQUEST)
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
          booking_end_date__gte=today)
    ).annotate(
        live_booking_count=Count(
            "appointments",
            filter=~Q(appointments__status=Appointment.Status.CANCELLED),
        )
    ).order_by("name")
    time_slots = TimeSlot.objects.filter(
        barangay=resident.barangay,
        is_active=True,
    ).order_by("start_time")
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
            ).exclude(status=Appointment.Status.CANCELLED)
            .values("time_slot_id")
            .annotate(count=Count("id"))
        }

    def serialize_time_slot(slot):
        booked = occupied_by_slot.get(slot.pk, 0)
        capacity = regular_slot_capacity(slot)
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
        for service in services:
            if not service.is_temporary:
                continue
            service_status = service.computed_status(now, service.live_booking_count)
            if service_status in {"expired", "cancelled", "deactivated"}:
                continue
            resident_booking = EventBooking.objects.filter(
                appointment__resident=resident, appointment__service=service
            ).exclude(status=EventBooking.Status.CANCELLED).first()
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
                "can_book": service_status in {"active", "ending_soon"},
                "is_event": True,
                "is_special_service": True,
                "is_booked": resident_booking is not None,
                "event_booking_id": resident_booking.pk if resident_booking else None,
            })
        priority = {"ending_soon": 0, "active": 1, "fully_booked": 2, "upcoming": 3}
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
        service = services.get(pk=request.data.get("service"))
        if service.is_temporary:
            appointment = create_special_service_booking(resident, service)
        else:
            time_slot = time_slots.get(pk=request.data.get("time_slot"))
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

    if request.method == "POST":
        try:
            appointment = resident.appointments.get(pk=request.data.get("appointment_id"))
        except (Appointment.DoesNotExist, TypeError, ValueError):
            return Response({"message": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "cancel":
            if appointment.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
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
                Notification.objects.create(
                    resident=resident, appointment=appointment,
                    notification_type=Notification.NotificationType.APPOINTMENT_CANCELLED,
                    title="Appointment Cancelled",
                    message="Your appointment has been cancelled.",
                )
            return Response({"success": True, "message": "Your appointment has been cancelled."})

        if action == "check_in":
            if appointment.appointment_date != timezone.localdate():
                return Response({"message": "Check-in is only available on your appointment date."}, status=status.HTTP_400_BAD_REQUEST)
            ticket = QueueTicket.objects.filter(appointment=appointment).first()
            if ticket:
                if ticket.notes == "Resident checked in and is waiting at the barangay.":
                    return Response({"success": True, "message": "You are already checked in."})
                ticket.notes = "Resident checked in and is waiting at the barangay."
                ticket.save(update_fields=["notes", "updated_at"])
            Notification.objects.create(
                resident=resident, appointment=appointment,
                notification_type=Notification.NotificationType.QUEUE_UPDATE,
                title="Check-in Complete",
                message=f"You are checked in with queue number {appointment.queue_number}.",
            )
            return Response({"success": True, "message": "You are checked in. Barangay staff have been notified."})

        return Response({"message": "Invalid queue action."}, status=status.HTTP_400_BAD_REQUEST)

    appointment = resident.appointments.select_related("service", "barangay", "time_slot").exclude(
        service__is_temporary=True,
    ).filter(
        appointment_date__gte=timezone.localdate(),
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED, Appointment.Status.ONGOING],
    ).order_by("appointment_date", "time_slot__start_time").first()
    if not appointment:
        return Response({"appointment": None})

    queue = QueueTicket.objects.filter(
        appointment__appointment_date=appointment.appointment_date,
        appointment__barangay=appointment.barangay,
        appointment__service=appointment.service,
    ).select_related("appointment")
    now_serving = queue.filter(status=QueueTicket.Status.NOW_SERVING).first()
    people_ahead = queue.filter(
        status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.NOW_SERVING],
        appointment__queue_number__lt=appointment.queue_number,
    ).count()
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
            "status": appointment.get_status_display(),
            "status_code": appointment.status,
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

    if request.method == "POST":
        try:
            appointment = resident.appointments.get(pk=request.data.get("appointment_id"))
        except (Appointment.DoesNotExist, TypeError, ValueError):
            return Response({"message": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "cancel":
            if appointment.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
                return Response({"message": "This appointment can no longer be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            if appointment.appointment_date < timezone.localdate():
                return Response({"message": "Past appointments can no longer be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                appointment.status = Appointment.Status.CANCELLED
                appointment.save(update_fields=["status", "updated_at"])
                QueueTicket.objects.filter(appointment=appointment).update(status=QueueTicket.Status.CANCELLED, updated_at=timezone.now())
                Notification.objects.create(
                    resident=resident, appointment=appointment,
                    notification_type=Notification.NotificationType.APPOINTMENT_CANCELLED,
                    title="Appointment Cancelled",
                    message="Your appointment has been cancelled.",
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

    appointments = resident.appointments.select_related("service", "barangay", "time_slot", "queue_ticket", "event_booking").order_by("-appointment_date", "-created_at")
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
        records.append({
            "id": appointment.pk,
            "appointment_id": f"QQ-{appointment.created_at.year}-{appointment.pk:05d}",
            "service": appointment.service.name,
            "service_fee": (
                "Free"
                if (appointment.service_fee_snapshot if appointment.service_fee_snapshot is not None else effective_service_fee(appointment.barangay, appointment.service)) == 0
                else f"₱{(appointment.service_fee_snapshot if appointment.service_fee_snapshot is not None else effective_service_fee(appointment.barangay, appointment.service)):,.2f}"
            ),
            "status": appointment.get_status_display(),
            "status_code": appointment.status,
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
    return Response({"transactions": records})


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
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def notifications_api(request):
    """List resident notifications and allow them to be marked as read."""
    resident = request.user.resident_profile

    if request.method == "POST":
        notification_id = request.data.get("notification_id")
        if notification_id:
            updated = resident.notifications.filter(pk=notification_id).update(is_read=True)
            if not updated:
                return Response({"message": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            resident.notifications.filter(is_read=False).update(is_read=True)
        return Response({"success": True})

    notifications = resident.notifications.order_by("-created_at")
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


def _chat_database_context(resident):
    services = Service.objects.filter(is_active=True).order_by("name")
    service_lines = [
        f"- {service.name}: requirements={service.requirements.strip() or 'not recorded'}; "
        f"estimated processing duration={service.estimated_duration} minutes"
        for service in services
    ]
    recent_notifications = resident.notifications.order_by("-created_at")[:3]
    notification_lines = [
        f"- {item.title}: {item.message} (read={'yes' if item.is_read else 'no'})"
        for item in recent_notifications
    ]
    appointment = resident.appointments.select_related(
        "service", "barangay", "time_slot"
    ).filter(
        appointment_date__gte=timezone.localdate(),
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED, Appointment.Status.ONGOING],
    ).order_by("appointment_date", "time_slot__start_time").first()

    if appointment:
        ticket = QueueTicket.objects.filter(appointment=appointment).first()
        queue = QueueTicket.objects.filter(
            appointment__appointment_date=appointment.appointment_date,
            appointment__barangay=appointment.barangay,
            appointment__service=appointment.service,
        ).select_related("appointment")
        now_serving = queue.filter(status=QueueTicket.Status.NOW_SERVING).first()
        people_ahead = queue.filter(
            status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.NOW_SERVING],
            appointment__queue_number__lt=appointment.queue_number,
        ).count()
        appointment_context = (
            f"Active appointment: ID QQ-{appointment.created_at.year}-{appointment.pk:05d}; "
            f"service={appointment.service.name}; date={appointment.appointment_date.isoformat()}; "
            f"time={appointment.time_slot.start_time.strftime('%I:%M %p')}-"
            f"{appointment.time_slot.end_time.strftime('%I:%M %p')}; "
            f"barangay={appointment.barangay.name}; queue number={appointment.queue_number}; "
            f"appointment status={appointment.get_status_display()}; "
            f"queue status={ticket.get_status_display() if ticket else 'not recorded'}; "
            f"now serving={now_serving.queue_number if now_serving else 'not recorded'}; "
            f"people ahead={people_ahead}; estimated wait={people_ahead * appointment.service.estimated_duration} minutes"
        )
    else:
        appointment_context = "Active appointment: none in the resident's QuickQueue record."

    context = "\n".join([
        f"Resident barangay: {resident.barangay.name}",
        appointment_context,
        "Available QuickQueue services:",
        *(service_lines or ["- No active services are currently recorded."]),
        "Recent QuickQueue notifications:",
        *(notification_lines or ["- No recent notifications are recorded."]),
        f"QuickQueue office hours: {settings.QUICKQUEUE_OFFICE_HOURS}",
        "Exact fees and unlisted availability are not present in this context.",
    ])
    return context, appointment


def _built_in_chat_reply(message, resident, appointment):
    """Provide safe QuickQueue guidance when the external AI provider is unavailable."""
    text = message.lower()
    services = list(Service.objects.filter(is_active=True).order_by("name"))
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
        if appointment.appointment_date != timezone.localdate():
            return (
                f"According to your QuickQueue record, check-in is available on "
                f"{appointment.appointment_date.strftime('%B %d, %Y')}. On that date, open Queue, "
                "find Appointment Actions, and tap Check In."
            )
        return "Open the Queue tab, find Appointment Actions, and tap Check In. Wait for QuickQueue to confirm that staff were notified."
    if "cancel" in text:
        if (appointment.status in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED)
                and appointment.appointment_date >= timezone.localdate()):
            return "You can cancel this appointment from the Queue or Transactions tab. Open the appointment, tap Cancel Appointment, and confirm."
        return f"According to your QuickQueue record, this appointment is {appointment.get_status_display()} and can no longer be cancelled in the app. Contact barangay staff if you need help."
    if any(word in text for word in ("queue", "number", "wait", "status", "track")):
        ticket = QueueTicket.objects.filter(appointment=appointment).first()
        queue_status = ticket.get_status_display() if ticket else "not recorded"
        return (
            f"According to your QuickQueue record, your queue number is {appointment.queue_number}, "
            f"your appointment is {appointment.get_status_display()}, and your queue status is {queue_status}. "
            "Open the Queue tab for live tracking or Transactions for appointment details."
        )
    if "notification" in text:
        return "Open Notifications to read the latest update. Use Queue when the notification requires a queue action, or Transactions to review the appointment details."
    if "office hour" in text or "opening hour" in text or "when are you open" in text:
        return f"The office hours shown in QuickQueue are {settings.QUICKQUEUE_OFFICE_HOURS}"
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


def _chat_suggestions(message, reply, has_appointment):
    text = f"{message} {reply}".lower()
    if has_appointment:
        if "called" in text or "now serving" in text:
            return ["What should I do when my number is called?", "Where can I see my queue number?", "How do I track my appointment?"]
        if "check in" in text:
            return ["When can I check in?", "Where can I see my queue number?", "How do I track my appointment?"]
        return ["How do I check in?", "Where can I see my queue number?", "How do I track my appointment?"]
    if "queue" in text or "wait" in text:
        return ["How do I book an appointment?", "What services are available?", "What are the requirements?"]
    if "appointment" in text or "book" in text:
        return ["What are the requirements?", "What services are available?", "Where can I see my queue?"]
    if "requirement" in text or "clearance" in text:
        return ["How do I book an appointment?", "What services are available?", "What is my queue status?"]
    if "service" in text or "fee" in text:
        return ["What are the requirements?", "How do I book an appointment?", "What is my queue status?"]
    return ["What services are available?", "How do I book an appointment?", "What is my queue status?"]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatRateThrottle])
def chat_api(request):
    message = str(request.data.get("message", "")).strip()
    if not message:
        return Response({"message": "Please enter a message."}, status=status.HTTP_400_BAD_REQUEST)
    if len(message) > 500:
        return Response({"message": "Please keep your message under 500 characters."}, status=status.HTTP_400_BAD_REQUEST)

    history = []
    for item in request.data.get("history", [])[-6:]:
        if not isinstance(item, dict) or item.get("role") not in ("resident", "assistant"):
            continue
        text = str(item.get("text", "")).strip()[:500]
        if text:
            history.append({"role": item["role"], "text": text})

    resident = request.user.resident_profile
    database_context, appointment = _chat_database_context(resident)
    used_ai = True
    try:
        reply = ask_gemini(message, database_context, history)
    except GeminiUnavailable:
        used_ai = False
        reply = _built_in_chat_reply(message, resident, appointment)
    reply = _format_chat_instructions(reply)

    return Response({
        "reply": reply,
        "suggestions": _chat_suggestions(message, reply, appointment is not None),
        "source": "QuickQueue records and AI guidance" if used_ai else "QuickQueue records and built-in guidance",
    })
