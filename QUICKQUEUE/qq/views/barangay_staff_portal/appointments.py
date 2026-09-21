import calendar
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Appointment, BarangayStaff, Notification, Service, TimeSlot

ACTIVE_STATUSES = [Appointment.Status.PENDING, Appointment.Status.CONFIRMED, Appointment.Status.ONGOING]


def _regular_staff_for(user):
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    if hasattr(user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        return None
    return staff


@login_required(login_url="signin")
def staff_appointments(request):
    staff = _regular_staff_for(request.user)
    if staff is None:
        return redirect("barangay_appointments")

    barangay = staff.barangay
    today = timezone.localdate()
    selected_date = today
    try:
        if request.GET.get("date"):
            selected_date = timezone.datetime.strptime(request.GET["date"], "%Y-%m-%d").date()
    except ValueError:
        pass
    base = Appointment.objects.filter(barangay=barangay).select_related("resident", "service", "time_slot")
    today_active = base.filter(appointment_date=today).exclude(
        status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED]
    )
    pending = base.filter(status=Appointment.Status.PENDING)
    confirmed_today = today_active.filter(status__in=[Appointment.Status.CONFIRMED, Appointment.Status.ONGOING])
    tomorrow_count = base.filter(appointment_date=today + timedelta(days=1), status__in=ACTIVE_STATUSES).count()
    slots = list(TimeSlot.objects.filter(barangay=barangay, is_active=True).order_by("start_time"))
    daily_capacity = sum(slot.max_appointments for slot in slots)

    month_start = selected_date.replace(day=1)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_counts = {row["appointment_date"]: row["count"] for row in base.filter(
        appointment_date__gte=month_start, appointment_date__lt=month_end, status__in=ACTIVE_STATUSES
    ).values("appointment_date").annotate(count=Count("id"))}
    calendar_weeks = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(selected_date.year, selected_date.month):
        calendar_weeks.append([{
            "date": day, "in_month": day.month == selected_date.month,
            "count": month_counts.get(day, 0),
            "remaining": max(daily_capacity - month_counts.get(day, 0), 0),
            "level": "full" if daily_capacity and month_counts.get(day, 0) >= daily_capacity
                     else "almost" if daily_capacity and month_counts.get(day, 0) >= daily_capacity * .75
                     else "available" if month_counts.get(day, 0) else "empty",
            "selected": day == selected_date,
        } for day in week])

    selected_qs = base.filter(appointment_date=selected_date).exclude(
        status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED]
    ).order_by("time_slot__start_time", "created_at")
    slot_counts = {row["time_slot_id"]: row["count"] for row in selected_qs.filter(
        status__in=ACTIVE_STATUSES
    ).values("time_slot_id").annotate(count=Count("id"))}
    selected_slots = []
    for slot in slots:
        booked = slot_counts.get(slot.pk, 0)
        selected_slots.append({"slot": slot, "booked": booked, "capacity": slot.max_appointments,
                               "remaining": max(slot.max_appointments - booked, 0),
                               "percent": round(booked / slot.max_appointments * 100) if slot.max_appointments else 0})

    tab = request.GET.get("tab", "pending")
    table_qs = pending
    if tab == "rejected":
        table_qs = base.filter(status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED])
    elif tab == "all":
        table_qs = base
    else:
        tab = "pending"
    search, service, date_filter = (request.GET.get("q", "").strip(),
                                    request.GET.get("service", ""), request.GET.get("filter_date", ""))
    if search:
        table_qs = table_qs.filter(Q(resident__first_name__icontains=search)
                                   | Q(resident__last_name__icontains=search)
                                   | Q(queue_number__icontains=search) | Q(service__name__icontains=search))
    if service.isdigit():
        table_qs = table_qs.filter(service_id=int(service))
    try:
        if date_filter:
            table_qs = table_qs.filter(appointment_date=timezone.datetime.strptime(date_filter, "%Y-%m-%d").date())
    except ValueError:
        pass
    return render(request, "barangay_staff/appointments.html", {
        "active_page": "appointments", "staff": staff, "barangay": barangay, "today": today,
        "today_total": today_active.count(), "pending_count": pending.count(),
        "confirmed_count": confirmed_today.count(), "tomorrow_count": tomorrow_count,
        "calendar_weeks": calendar_weeks, "daily_capacity": daily_capacity,
        "month_label": selected_date.strftime("%B %Y"), "selected_date": selected_date,
        "selected_appointments": selected_qs, "selected_slots": selected_slots,
        "selected_count": selected_qs.count(), "selected_remaining": max(daily_capacity - selected_qs.count(), 0),
        "appointments": table_qs.order_by("appointment_date", "time_slot__start_time")[:50],
        "tab": tab, "services": Service.objects.filter(is_active=True).order_by("name"),
        "filters": {"q": search, "service": service, "filter_date": date_filter},
        "unread_notifications": Notification.objects.filter(appointment__barangay=barangay, admin_is_read=False).count(),
    })


@login_required(login_url="signin")
@require_POST
def staff_review_appointment(request, pk):
    staff = _regular_staff_for(request.user)
    if staff is None:
        return redirect("barangay_appointments")

    appointment = get_object_or_404(
        Appointment.objects.select_related("resident", "service", "time_slot"),
        pk=pk,
        barangay=staff.barangay,
    )
    if appointment.status != Appointment.Status.PENDING:
        messages.error(request, "Only pending appointments can be reviewed.")
        return redirect("staff_appointments")

    decision = request.POST.get("decision")
    if decision == "approve":
        appointment.status = Appointment.Status.CONFIRMED
        title = "Appointment Confirmed"
        notification_type = Notification.NotificationType.APPOINTMENT_CONFIRMED
        message = (
            f"Your appointment for {appointment.service.name} on {appointment.appointment_date} "
            f"at {appointment.time_slot.start_time.strftime('%I:%M %p')} has been confirmed. "
            f"Queue number: {appointment.queue_number}."
        )
        feedback = f"Approved the appointment of {appointment.resident}."
    elif decision == "reject":
        appointment.status = Appointment.Status.CANCELLED
        title = "Appointment Rejected"
        notification_type = Notification.NotificationType.APPOINTMENT_CANCELLED
        message = (
            f"Your appointment for {appointment.service.name} on {appointment.appointment_date} "
            "was not approved. Please book another available schedule."
        )
        feedback = f"Rejected the appointment of {appointment.resident}."
    else:
        messages.error(request, "Choose Approve Appointment or Reject Appointment.")
        return redirect("staff_appointments")

    appointment.save(update_fields=["status", "updated_at"])
    Notification.objects.create(
        resident=appointment.resident,
        appointment=appointment,
        notification_type=notification_type,
        title=title,
        message=message,
    )
    messages.success(request, feedback)
    return redirect("staff_appointments")
