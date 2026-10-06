from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from qq.models import Appointment, BarangayStaff, EventBooking, Notification, Service
import json


def _staff_for(user):
    if hasattr(user, "barangay_profile"):
        raise Http404("This page is available to staff accounts only.")
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to staff accounts only.") from error
    if not staff.is_active:
        raise Http404("This staff account is inactive.")
    return staff


@login_required(login_url="signin")
def staff_temporary_services(request):
    staff = _staff_for(request.user)
    offerings = Service.objects.filter(is_temporary=True, barangay=staff.barangay).order_by("-event_start_date")
    selected = request.GET.get("status", "all")
    now = timezone.now()
    records = []
    for offering in offerings:
        count = offering.appointments.exclude(status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED]).count()
        offering.display_status = offering.computed_status(now, count)
        offering.booking_count = count
        if selected == "all" or offering.display_status == selected:
            records.append(offering)
    return render(request, "barangay_staff/temporary_services.html", {
        "active_page": "events", "staff": staff, "offerings": records,
        "selected_status": selected, "now": now,
    })


@login_required(login_url="signin")
def staff_temporary_service_form(request, pk=None):
    staff = _staff_for(request.user)
    offering = get_object_or_404(Service, pk=pk, is_temporary=True, barangay=staff.barangay) if pk else None
    if offering and offering.computed_status() in {"expired", "cancelled"}:
        messages.error(request, "Expired and cancelled records are read-only.")
        return redirect("staff_temporary_services")
    if request.method == "POST":
        try:
            event_start_date = date.fromisoformat(request.POST.get("event_start_date", ""))
            event_end_date = date.fromisoformat(request.POST.get("event_end_date", ""))
            booking_start_date = date.fromisoformat(request.POST.get("booking_start_date", ""))
            booking_end_date = date.fromisoformat(request.POST.get("booking_end_date", ""))
            capacity = int(request.POST["capacity"])
            if offering and offering.appointments.exists():
                critical_change = (
                    offering.event_start_date != event_start_date or
                    offering.event_end_date != event_end_date or
                    offering.booking_start_date != booking_start_date or
                    offering.booking_end_date != booking_end_date or
                    offering.capacity != capacity
                )
                if critical_change:
                    raise ValidationError("This event already has bookings. Its event dates, booking period, and capacity cannot be changed.")
            instance = offering or Service(is_temporary=True, barangay=staff.barangay, created_by=request.user)
            instance.name = request.POST.get("name", "").strip()
            instance.temporary_type = request.POST.get("temporary_type", "")
            instance.description = request.POST.get("description", "").strip()
            instance.requirements = request.POST.get("requirements", "").strip()
            instance.location = request.POST.get("location", "").strip()
            instance.event_start_date, instance.event_end_date = event_start_date, event_end_date
            instance.booking_start_date, instance.booking_end_date = booking_start_date, booking_end_date
            instance.capacity = capacity
            instance.estimated_duration = instance.estimated_duration or 15
            instance.code = request.POST.get("code", "EVT").strip().upper()[:5]
            instance.full_clean()
            instance.save()
            messages.success(request, "Event/service saved successfully.")
            return redirect("staff_temporary_services")
        except (ValidationError, ValueError, KeyError) as error:
            message = "; ".join(error.messages) if isinstance(error, ValidationError) else "Enter a complete and valid schedule."
            messages.error(request, message)
    return render(request, "barangay_staff/temporary_service_form.html", {
        "active_page": "events", "staff": staff, "offering": offering,
    })


@login_required(login_url="signin")
def staff_temporary_service_action(request, pk):
    staff = _staff_for(request.user)
    if request.method != "POST":
        return redirect("staff_temporary_services")
    offering = get_object_or_404(Service, pk=pk, is_temporary=True, barangay=staff.barangay)
    action = request.POST.get("action")
    if action == "cancel" and offering.computed_status() not in {"expired", "cancelled"}:
        offering.lifecycle = Service.Lifecycle.CANCELLED
        offering.save(update_fields=["lifecycle", "updated_at"])
        EventBooking.objects.filter(appointment__service=offering).update(
            status=EventBooking.Status.CANCELLED,
            cancelled_at=timezone.now(),
            updated_at=timezone.now(),
        )
        for appointment in offering.appointments.select_related("resident"):
            Notification.objects.get_or_create(
                resident=appointment.resident, appointment=appointment,
                notification_type=Notification.NotificationType.APPOINTMENT_CANCELLED,
                title=f"{offering.name} Cancelled",
                defaults={"message": f"{offering.name} has been cancelled. Your appointment record remains available in Transactions."},
            )
        messages.success(request, "The event/service was cancelled and affected residents were notified.")
    elif action == "deactivate" and offering.computed_status() not in {"expired", "cancelled"}:
        offering.is_active = False
        offering.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "The event/service is no longer accepting bookings.")
    return redirect("staff_temporary_services")


def _scan_payload(booking, now):
    appointment, event = booking.appointment, booking.appointment.service
    resident = appointment.resident
    base = {
        "event_name": event.name,
        "resident_name": resident.full_name if hasattr(resident, "full_name") else str(resident),
        "booking_reference": booking.booking_reference,
        "event_datetime": f"{event.event_start_date:%b %d, %Y} – {event.event_end_date:%b %d, %Y}",
        "checked_in_at": timezone.localtime(booking.checked_in_at).strftime("%b %d, %Y %I:%M %p") if booking.checked_in_at else None,
    }
    if booking.status == EventBooking.Status.CANCELLED or appointment.status == Appointment.Status.CANCELLED or event.lifecycle == Service.Lifecycle.CANCELLED:
        return {**base, "result": "cancelled", "message": "Booking Cancelled", "can_check_in": False}
    today = timezone.localdate(now)
    if event.event_end_date and today > event.event_end_date:
        return {**base, "result": "expired", "message": "Event Booking Expired", "can_check_in": False}
    if booking.status == EventBooking.Status.CHECKED_IN:
        return {**base, "result": "checked_in", "message": "Already Checked In", "can_check_in": False}
    if not event.event_start_date or today < event.event_start_date:
        return {**base, "result": "upcoming", "message": "Event Has Not Started", "can_check_in": False}
    return {**base, "result": "valid", "message": "Valid Booking", "can_check_in": True}


@login_required(login_url="signin")
def staff_event_scanner(request):
    staff = _staff_for(request.user)
    if request.method == "GET":
        return render(request, "barangay_staff/event_scanner.html", {"active_page": "event_scanner", "staff": staff})
    try:
        body = json.loads(request.body or "{}")
        booking_id = EventBooking.booking_id_from_token(str(body.get("token", "")))
    except (ValueError, KeyError, signing.BadSignature, json.JSONDecodeError):
        return JsonResponse({"result": "invalid", "message": "Invalid QR Code", "can_check_in": False}, status=400)
    try:
        with transaction.atomic():
            booking = EventBooking.objects.select_for_update().select_related(
                "appointment__service", "appointment__resident"
            ).get(booking_id=booking_id, appointment__barangay=staff.barangay)
            payload = _scan_payload(booking, timezone.now())
            if body.get("action") == "check_in":
                if not payload["can_check_in"]:
                    return JsonResponse(payload, status=409)
                booking.status = EventBooking.Status.CHECKED_IN
                booking.checked_in_at = timezone.now()
                booking.checked_in_by = request.user
                booking.save(update_fields=["status", "checked_in_at", "checked_in_by", "updated_at"])
                payload = _scan_payload(booking, timezone.now())
                payload["message"] = "Check-In Successful"
            return JsonResponse(payload)
    except EventBooking.DoesNotExist:
        return JsonResponse({"result": "not_found", "message": "Booking Not Found", "can_check_in": False}, status=404)
