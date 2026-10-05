from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from qq.models import Appointment, BarangayStaff, EventBooking, Notification, Service, TimeSlot
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


def _local_datetime(value):
    parsed = datetime.fromisoformat(value)
    return timezone.make_aware(parsed, timezone.get_current_timezone()) if timezone.is_naive(parsed) else parsed


@login_required(login_url="signin")
def staff_temporary_services(request):
    staff = _staff_for(request.user)
    offerings = Service.objects.filter(is_temporary=True, barangay=staff.barangay).prefetch_related(
        "available_time_slots"
    ).order_by("-start_datetime")
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
    slots = TimeSlot.objects.filter(barangay=staff.barangay, is_active=True).order_by("start_time")
    if request.method == "POST":
        try:
            chosen_slots = list(slots.filter(pk__in=request.POST.getlist("time_slots")))
            start = _local_datetime(request.POST.get("start_datetime", ""))
            end = _local_datetime(request.POST.get("end_datetime", ""))
            capacity = int(request.POST["capacity"]) if request.POST.get("capacity") else None
            slot_duration = int(request.POST["slot_duration"]) if request.POST.get("slot_duration") else None
            if offering and offering.appointments.exists():
                old_slot_ids = set(offering.available_time_slots.values_list("pk", flat=True))
                critical_change = (
                    offering.start_datetime != start or offering.end_datetime != end or
                    offering.capacity != capacity or old_slot_ids != {slot.pk for slot in chosen_slots}
                )
                if critical_change:
                    raise ValidationError("This event already has existing appointments. Its schedule, slots, and capacity cannot be changed.")
            instance = offering or Service(is_temporary=True, barangay=staff.barangay, created_by=request.user)
            instance.name = request.POST.get("name", "").strip()
            instance.temporary_type = request.POST.get("temporary_type", "")
            instance.description = request.POST.get("description", "").strip()
            instance.requirements = request.POST.get("requirements", "").strip()
            instance.location = request.POST.get("location", "").strip()
            instance.start_datetime, instance.end_datetime = start, end
            instance.slot_duration, instance.capacity = slot_duration, capacity
            instance.estimated_duration = slot_duration or instance.estimated_duration or 15
            instance.code = request.POST.get("code", "EVT").strip().upper()[:5]
            instance.full_clean()
            instance.save()
            instance.available_time_slots.set(chosen_slots)
            messages.success(request, "Event/service saved successfully.")
            return redirect("staff_temporary_services")
        except (ValidationError, ValueError, KeyError) as error:
            message = "; ".join(error.messages) if isinstance(error, ValidationError) else "Enter a complete and valid schedule."
            messages.error(request, message)
    return render(request, "barangay_staff/temporary_service_form.html", {
        "active_page": "events", "staff": staff, "offering": offering, "slots": slots,
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
        "event_datetime": f"{event.start_datetime:%b %d, %Y %I:%M %p} – {event.end_datetime:%b %d, %Y %I:%M %p}",
        "checked_in_at": timezone.localtime(booking.checked_in_at).strftime("%b %d, %Y %I:%M %p") if booking.checked_in_at else None,
    }
    if booking.status == EventBooking.Status.CANCELLED or appointment.status == Appointment.Status.CANCELLED or event.lifecycle == Service.Lifecycle.CANCELLED:
        return {**base, "result": "cancelled", "message": "Booking Cancelled", "can_check_in": False}
    if event.end_datetime and now >= event.end_datetime:
        return {**base, "result": "expired", "message": "Event Booking Expired", "can_check_in": False}
    if booking.status == EventBooking.Status.CHECKED_IN:
        return {**base, "result": "checked_in", "message": "Already Checked In", "can_check_in": False}
    if not event.start_datetime or now < event.start_datetime:
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
