from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Max
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from qq.models import (
    Appointment, Barangay, BarangayBookingConfiguration, BarangayServiceConfiguration,
    BarangayStaff, ClosedAppointmentDate, Notification, Service, TimeSlot,
)


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        return user.staff_profile.barangay
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


def _staff_for(user):
    try:
        return user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("No staff profile is linked to this account.") from error


@login_required(login_url="signin")
def barangay_settings(request):
    """Display and update the signed-in barangay staff member's account settings."""
    if (
        hasattr(request.user, "staff_profile")
        and not hasattr(request.user, "barangay_profile")
        and request.user.staff_profile.role != BarangayStaff.Role.ADMIN
    ):
        return redirect("staff_settings")
    barangay = _barangay_for(request.user)
    staff = _staff_for(request.user)
    today = timezone.localdate()
    active_tab = request.GET.get("tab", "profile")
    allowed_tabs = ("services", "slots", "calendar", "profile", "password")
    if active_tab not in allowed_tabs:
        active_tab = "profile"

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            _update_profile(request, staff)
            active_tab = "profile"
        elif action == "password":
            _update_password(request)
            active_tab = "password"
        elif action == "service":
            _update_service_configuration(request, barangay)
            active_tab = "services"
        elif action == "booking":
            _update_booking_configuration(request, barangay)
            active_tab = "slots"
        elif action == "slot":
            _update_time_slot(request, barangay)
            active_tab = "slots"
        elif action == "calendar":
            _update_calendar(request, barangay)
            active_tab = "calendar"
        return redirect(f"{reverse('barangay_settings')}?tab={active_tab}")

    last_login = request.user.last_login
    booking_configuration, _ = BarangayBookingConfiguration.objects.get_or_create(barangay=barangay)
    regular_services = list(Service.objects.filter(is_temporary=False).order_by("name"))
    saved_configurations = {
        item.service_id: item
        for item in BarangayServiceConfiguration.objects.filter(barangay=barangay, service__in=regular_services)
    }
    service_rows = []
    for service in regular_services:
        configuration = saved_configurations.get(service.pk)
        service_rows.append({
            "service": service,
            "fee": configuration.fee if configuration else Decimal("0.00"),
            "duration": configuration.estimated_duration if configuration else service.estimated_duration,
            "is_active": configuration.is_active if configuration else service.is_active,
        })
    return render(
        request,
        "barangay_admin/settings.html",
        {
            "barangay": barangay,
            "staff": staff,
            "today": today,
            "active_page": "settings",
            "active_tab": active_tab,
            "last_login": last_login,
            "service_rows": service_rows,
            "booking_configuration": booking_configuration,
            "time_slots": TimeSlot.objects.filter(barangay=barangay).order_by("start_time"),
            "closed_dates": ClosedAppointmentDate.objects.filter(
                barangay=barangay, date__gte=today
            ).order_by("date"),
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )


def _update_service_configuration(request, barangay):
    try:
        service = Service.objects.get(pk=request.POST.get("service_id"), is_temporary=False)
        fee = Decimal(request.POST.get("fee", "0")).quantize(Decimal("0.01"))
        duration = int(request.POST.get("estimated_duration", "0"))
    except (Service.DoesNotExist, TypeError, ValueError, InvalidOperation):
        messages.error(request, "Enter a valid service fee and processing time.")
        return
    if fee < 0:
        messages.error(request, "Service fees cannot be negative.")
        return
    if duration < 1 or duration > 480:
        messages.error(request, "Estimated processing time must be between 1 and 480 minutes.")
        return
    BarangayServiceConfiguration.objects.update_or_create(
        barangay=barangay,
        service=service,
        defaults={
            "fee": fee,
            "estimated_duration": duration,
            "is_active": request.POST.get("is_active") == "on",
        },
    )
    messages.success(request, f"Updated {service.name}.")


def _update_booking_configuration(request, barangay):
    try:
        daily_capacity = int(request.POST.get("daily_capacity", "0"))
        start_time = datetime.strptime(request.POST["office_start_time"], "%H:%M").time()
        end_time = datetime.strptime(request.POST["office_end_time"], "%H:%M").time()
    except (KeyError, TypeError, ValueError):
        messages.error(request, "Enter valid booking capacity and office hours.")
        return
    if daily_capacity < 1 or daily_capacity > 300 or end_time <= start_time:
        messages.error(request, "Daily capacity must be 1–300 and office closing time must be later than opening time.")
        return
    highest_daily = (
        Appointment.objects.filter(barangay=barangay, time_slot__isnull=False)
        .exclude(status=Appointment.Status.CANCELLED)
        .values("appointment_date").annotate(total=Count("id")).aggregate(maximum=Max("total"))["maximum"] or 0
    )
    if daily_capacity < highest_daily:
        messages.error(request, f"Daily capacity cannot be below the existing booked total of {highest_daily}.")
        return
    BarangayBookingConfiguration.objects.update_or_create(
        barangay=barangay,
        defaults={"daily_capacity": daily_capacity, "office_start_time": start_time, "office_end_time": end_time},
    )
    messages.success(request, "Appointment capacity and office hours updated.")


def _update_time_slot(request, barangay):
    try:
        slot = TimeSlot.objects.get(pk=request.POST.get("slot_id"), barangay=barangay)
        start_time = request.POST["start_time"]
        end_time = request.POST["end_time"]
        capacity = int(request.POST.get("max_appointments", "0"))
    except (TimeSlot.DoesNotExist, KeyError, TypeError, ValueError):
        messages.error(request, "Select a valid time slot and capacity.")
        return
    highest_occupancy = (
        slot.appointments.exclude(status=Appointment.Status.CANCELLED)
        .values("appointment_date").annotate(total=Count("id")).aggregate(maximum=Max("total"))["maximum"] or 0
    )
    if capacity < max(highest_occupancy, 1) or capacity > 5:
        messages.error(request, f"Slot capacity must be {max(highest_occupancy, 1)}–5 based on existing bookings.")
        return
    from datetime import time as time_value
    try:
        start_parts = [int(part) for part in start_time.split(":")]
        end_parts = [int(part) for part in end_time.split(":")]
        slot.start_time = time_value(*start_parts)
        slot.end_time = time_value(*end_parts)
        if slot.end_time <= slot.start_time:
            raise ValueError
        slot.max_appointments = capacity
        slot.is_active = request.POST.get("is_active") == "on"
        slot.save()
    except (IntegrityError, TypeError, ValueError):
        messages.error(request, "Time windows must be valid, unique, and end after they start.")
        return
    messages.success(request, "Appointment time slot updated.")


def _update_calendar(request, barangay):
    try:
        selected_date = date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        messages.error(request, "Select a valid date.")
        return
    if selected_date < timezone.localdate():
        messages.error(request, "Past dates are already closed and cannot be edited.")
        return
    if request.POST.get("calendar_action") == "reopen":
        ClosedAppointmentDate.objects.filter(barangay=barangay, date=selected_date).delete()
        messages.success(request, f"Bookings reopened for {selected_date:%B %d, %Y}.")
        return
    existing = Appointment.objects.filter(barangay=barangay, appointment_date=selected_date).exclude(
        status=Appointment.Status.CANCELLED
    ).count()
    if existing and request.POST.get("confirm_existing") != "on":
        messages.error(request, f"{existing} existing appointment(s) will remain on this date. Check the warning box to close it.")
        return
    ClosedAppointmentDate.objects.update_or_create(
        barangay=barangay,
        date=selected_date,
        defaults={"reason": request.POST.get("reason", "").strip(), "created_by": request.user},
    )
    messages.success(request, f"Bookings closed for {selected_date:%B %d, %Y}; existing appointments were preserved.")


def _update_profile(request, staff):
    user = request.user
    fields = ("first_name", "last_name", "middle_name", "email", "contact_number")
    values = {field: request.POST.get(field, "").strip() for field in fields}
    photo = request.FILES.get("profile_photo")
    if not values["first_name"] or not values["last_name"]:
        messages.error(request, "First name and last name are required.")
        return
    if photo:
        allowed_types = {"image/jpeg", "image/png"}
        if photo.content_type not in allowed_types or Path(photo.name).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            messages.error(request, "Profile photo must be a JPG or PNG image.")
            return
        if photo.size > 5 * 1024 * 1024:
            messages.error(request, "Profile photo must not exceed 5MB.")
            return
    try:
        with transaction.atomic():
            for field, value in values.items():
                setattr(staff, field, value)
            if photo:
                staff.profile_photo = photo
            staff.save()
            user.first_name = values["first_name"]
            user.last_name = values["last_name"]
            user.email = values["email"]
            user.save(update_fields=("first_name", "last_name", "email"))
        messages.success(request, "Your profile has been updated.")
    except IntegrityError:
        messages.error(request, "That email address is already in use.")


def _update_password(request):
    user = request.user
    current = request.POST.get("current_password", "")
    new = request.POST.get("new_password", "")
    confirm = request.POST.get("confirm_password", "")
    if not user.check_password(current):
        messages.error(request, "Your current password is incorrect.")
        return
    if new != confirm:
        messages.error(request, "The new password and confirmation do not match.")
        return
    try:
        validate_password(new, user)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return
    user.set_password(new)
    user.save()
    update_session_auth_hash(request, user)
    messages.success(request, "Password updated successfully.")
