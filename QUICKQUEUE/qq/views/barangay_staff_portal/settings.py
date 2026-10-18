from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from qq.models import (
    Appointment,
    BarangayServiceConfiguration,
    BarangayStaff,
    ClosedAppointmentDate,
    Service,
)
from qq.views.barangay_settings import _update_password, _update_profile


@login_required(login_url="signin")
def staff_settings(request):
    try:
        staff = request.user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_settings")
    active_tab = request.GET.get("tab", "services")
    if active_tab not in {"services", "booking", "calendar", "profile", "password"}:
        active_tab = "profile"
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "password":
            _update_password(request)
            active_tab = "password"
        elif action == "profile":
            _update_profile(request, staff)
            active_tab = "profile"
        elif action == "service":
            _update_service_configuration(request, staff)
            active_tab = "services"
        elif action == "calendar":
            _update_calendar(request, staff)
            active_tab = "calendar"
        elif action == "booking":
            _update_booking_capacity(request, staff)
            active_tab = "booking"
        return redirect(f"/barangay/staff/settings/?tab={active_tab}")
    services = list(Service.objects.filter(is_temporary=False).order_by("name"))
    configurations = {
        item.service_id: item
        for item in BarangayServiceConfiguration.objects.filter(
            barangay=staff.barangay, service__in=services
        )
    }
    service_rows = [{
        "service": service,
        "fee": configurations[service.pk].fee if service.pk in configurations else Decimal("0.00"),
        "duration": configurations[service.pk].estimated_duration if service.pk in configurations else service.estimated_duration,
    } for service in services]
    today = timezone.localdate()
    return render(request, "barangay_staff/settings.html", {
        "active_page": "settings", "active_tab": active_tab,
        "staff": staff, "barangay": staff.barangay,
        "daily_booking_capacity": staff.barangay.daily_booking_capacity,
        "today": today, "service_rows": service_rows,
        "closed_dates": ClosedAppointmentDate.objects.filter(
            barangay=staff.barangay, date__gte=today
        ).order_by("date"),
    })


@transaction.atomic
def _update_booking_capacity(request, staff):
    raw_capacity = request.POST.get("daily_booking_capacity", "").strip()
    if not raw_capacity.isascii() or not raw_capacity.isdecimal():
        messages.error(request, "Daily booking capacity must be a positive whole number.")
        return
    capacity = int(raw_capacity)
    if capacity < 1 or capacity > 2147483647:
        messages.error(request, "Daily booking capacity must be a positive whole number.")
        return

    from qq.models import Barangay

    barangay = Barangay.objects.select_for_update().get(pk=staff.barangay_id)
    busiest_day = (
        Appointment.objects.filter(
            barangay=barangay,
            service__is_temporary=False,
            time_slot__isnull=False,
            appointment_date__gte=timezone.localdate(),
        )
        .exclude(status=Appointment.Status.CANCELLED)
        .values("appointment_date")
        .annotate(booked=Count("id"))
        .order_by("-booked", "appointment_date")
        .first()
    )
    barangay.daily_booking_capacity = capacity
    barangay.save(update_fields=["daily_booking_capacity", "updated_at"])

    if busiest_day and busiest_day["booked"] > capacity:
        messages.warning(
            request,
            f"Capacity saved. {busiest_day['booked']} existing appointments on "
            f"{busiest_day['appointment_date']:%B %d, %Y} were preserved and exceed the new limit.",
        )
    else:
        messages.success(request, "Daily booking capacity updated.")


def _update_service_configuration(request, staff):
    try:
        service = Service.objects.get(pk=request.POST.get("service_id"), is_temporary=False)
        fee = Decimal(request.POST.get("fee", "0")).quantize(Decimal("0.01"))
        duration = int(request.POST.get("estimated_duration", "0"))
    except (Service.DoesNotExist, TypeError, ValueError, InvalidOperation):
        messages.error(request, "Enter a valid service fee and processing time.")
        return
    if fee < 0 or duration < 1 or duration > 480:
        messages.error(request, "Fees cannot be negative and processing time must be 1 to 480 minutes.")
        return
    BarangayServiceConfiguration.objects.update_or_create(
        barangay=staff.barangay,
        service=service,
        defaults={"fee": fee, "estimated_duration": duration},
    )
    messages.success(request, f"Updated {service.name}.")


def _update_calendar(request, staff):
    try:
        selected_date = date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        messages.error(request, "Select a valid date.")
        return
    if selected_date < timezone.localdate():
        messages.error(request, "Past dates are already closed and cannot be edited.")
        return
    if request.POST.get("calendar_action") == "reopen":
        ClosedAppointmentDate.objects.filter(
            barangay=staff.barangay, date=selected_date
        ).delete()
        messages.success(request, f"Bookings reopened for {selected_date:%B %d, %Y}.")
        return
    existing = Appointment.objects.filter(
        barangay=staff.barangay, appointment_date=selected_date
    ).exclude(status=Appointment.Status.CANCELLED).count()
    if existing and request.POST.get("confirm_existing") != "on":
        messages.error(
            request,
            f"{existing} existing appointment(s) will remain. Confirm this before closing the date.",
        )
        return
    ClosedAppointmentDate.objects.update_or_create(
        barangay=staff.barangay,
        date=selected_date,
        defaults={"reason": request.POST.get("reason", "").strip(), "created_by": request.user},
    )
    messages.success(request, f"New bookings closed for {selected_date:%B %d, %Y}.")
