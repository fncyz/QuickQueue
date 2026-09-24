from django.contrib.auth import authenticate
from qq.models import Barangay
from .serializers import BarangaySerializer, DocumentTemplateSerializer

from rest_framework import status
from rest_framework.decorators import api_view
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
from django.db import transaction
from django.utils import timezone
from datetime import date
import re

from qq.models import Appointment, BarangayStaff, DocumentTemplate, Notification, QueueTicket, Service, TimeSlot
from qq.services.appointment_service import create_appointment
from qq.services.timeslot_service import ensure_default_time_slots


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

    resident = Resident.objects.get(user=user)
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
    services = Service.objects.filter(is_active=True).order_by("name")
    time_slots = TimeSlot.objects.filter(
        barangay=resident.barangay,
        is_active=True,
    ).order_by("start_time")

    if request.method == "GET":
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
            "services": [{"id": service.pk, "name": service.name} for service in services],
            "time_slots": [{
                "id": slot.pk,
                "label": f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}",
            } for slot in time_slots],
        })

    try:
        service = services.get(pk=request.data.get("service"))
        time_slot = time_slots.get(pk=request.data.get("time_slot"))
        appointment_date = date.fromisoformat(request.data.get("appointment_date", ""))
        if appointment_date < date.today():
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

    return Response({
        "success": True,
        "message": "Appointment submitted successfully.",
        "appointment_id": f"QQ-{appointment.created_at.year}-{appointment.pk:05d}",
        "queue_number": appointment.queue_number,
        "service": appointment.service.name,
        "appointment_date": appointment.appointment_date.strftime("%B %d, %Y"),
        "time_slot": f"{appointment.time_slot.start_time.strftime('%I:%M %p')} - {appointment.time_slot.end_time.strftime('%I:%M %p')}",
        "status": appointment.get_status_display(),
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
            with transaction.atomic():
                appointment.status = Appointment.Status.CANCELLED
                appointment.save(update_fields=["status", "updated_at"])
                QueueTicket.objects.filter(appointment=appointment).update(status=QueueTicket.Status.CANCELLED, updated_at=timezone.now())
            return Response({"success": True, "message": "Your appointment has been cancelled."})

        if action == "check_in":
            if appointment.appointment_date != date.today():
                return Response({"message": "Check-in is only available on your appointment date."}, status=status.HTTP_400_BAD_REQUEST)
            ticket = QueueTicket.objects.filter(appointment=appointment).first()
            if ticket:
                ticket.notes = "Resident checked in and is waiting at the barangay."
                ticket.save(update_fields=["notes", "updated_at"])
            return Response({"success": True, "message": "You are checked in. Barangay staff have been notified."})

        return Response({"message": "Invalid queue action."}, status=status.HTTP_400_BAD_REQUEST)

    appointment = resident.appointments.select_related("service", "barangay", "time_slot").filter(
        appointment_date__gte=date.today(),
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
            "service_fee": "To be confirmed at barangay",
            "date": appointment.appointment_date.strftime("%B %d, %Y"),
            "time_slot": f"{appointment.time_slot.start_time.strftime('%I:%M %p')} - {appointment.time_slot.end_time.strftime('%I:%M %p')}",
            "barangay": appointment.barangay.name,
            "queue_number": appointment.queue_number,
            "status": appointment.get_status_display(),
            "status_code": appointment.status,
            "now_serving": now_serving.queue_number if now_serving else "—",
            "people_ahead": people_ahead,
            "estimated_wait": people_ahead * appointment.service.estimated_duration,
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
            with transaction.atomic():
                appointment.status = Appointment.Status.CANCELLED
                appointment.save(update_fields=["status", "updated_at"])
                QueueTicket.objects.filter(appointment=appointment).update(status=QueueTicket.Status.CANCELLED, updated_at=timezone.now())
            return Response({"success": True, "message": "Appointment cancelled."})

        if action == "delete":
            if appointment.status not in (Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.MISSED):
                return Response({"message": "Only completed, cancelled, or expired appointments can be deleted."}, status=status.HTTP_400_BAD_REQUEST)
            appointment.delete()
            return Response({"success": True, "message": "Appointment deleted from your history."})

        return Response({"message": "Invalid transaction action."}, status=status.HTTP_400_BAD_REQUEST)

    appointments = resident.appointments.select_related("service", "barangay", "time_slot").order_by("-appointment_date", "-created_at")
    records = []
    for appointment in appointments:
        ticket = QueueTicket.objects.filter(appointment=appointment).first()
        records.append({
            "id": appointment.pk,
            "appointment_id": f"QQ-{appointment.created_at.year}-{appointment.pk:05d}",
            "service": appointment.service.name,
            "status": appointment.get_status_display(),
            "status_code": appointment.status,
            "date_booked": appointment.created_at.strftime("%B %d, %Y"),
            "appointment_date": appointment.appointment_date.strftime("%B %d, %Y"),
            "date_claimed": ticket.claimed_at.strftime("%B %d, %Y") if ticket and ticket.claimed_at else None,
            "time_slot": f"{appointment.time_slot.start_time.strftime('%I:%M %p')} - {appointment.time_slot.end_time.strftime('%I:%M %p')}",
            "barangay": appointment.barangay.name,
            "queue_number": appointment.queue_number,
        })
    return Response({"transactions": records})


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

    notifications = resident.notifications.select_related("appointment").order_by("-created_at")
    return Response({
        "unread_count": notifications.filter(is_read=False).count(),
        "notifications": [{
            "id": item.pk,
            "type": item.notification_type,
            "title": item.title,
            "message": item.message,
            "is_read": item.is_read,
            "appointment_id": item.appointment_id,
            "created_at": item.created_at.isoformat(),
        } for item in notifications],
    })
