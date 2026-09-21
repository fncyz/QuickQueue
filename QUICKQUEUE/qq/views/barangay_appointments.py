from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Appointment, Barangay, BarangayStaff, Notification, Service, TimeSlot


ACTIVE_BOOKING_STATUSES = [
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
    Appointment.Status.ONGOING,
]


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        return user.staff_profile.barangay
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


def _queue_series(queue_number):
    if not queue_number:
        return "—"
    if "-" in queue_number:
        return queue_number.split("-", 1)[0]
    return queue_number[:1]


def _slot_availability(barangay, day):
    slots = TimeSlot.objects.filter(barangay=barangay, is_active=True).order_by("start_time")
    booked_map = {
        row["time_slot_id"]: row["count"]
        for row in Appointment.objects.filter(
            barangay=barangay,
            appointment_date=day,
            status__in=ACTIVE_BOOKING_STATUSES,
        )
        .values("time_slot_id")
        .annotate(count=Count("id"))
    }

    availability = []
    for slot in slots:
        booked = booked_map.get(slot.id, 0)
        capacity = slot.max_appointments
        remaining = max(capacity - booked, 0)
        percent = round((booked / capacity) * 100) if capacity else 0

        if booked >= capacity:
            level, label = "full", "FULL"
        elif remaining == 1:
            level, label = "almost", "1 Slot Remaining"
        elif booked == 0:
            level, label = "empty", f"{capacity} Slots Remaining"
        else:
            level, label = "available", f"{remaining} Slots Remaining"

        series = chr(65 + (len(availability) % 26))
        availability.append(
            {
                "slot": slot,
                "booked": booked,
                "capacity": capacity,
                "percent": min(percent, 100),
                "level": level,
                "label": label,
                "series_label": f"{series}01 - {series}{capacity:02d}",
            }
        )
    return availability


@login_required(login_url="signin")
def barangay_appointments(request):
    """Appointments management page for barangay staff."""
    if (
        hasattr(request.user, "staff_profile")
        and not hasattr(request.user, "barangay_profile")
        and request.user.staff_profile.role != BarangayStaff.Role.ADMIN
    ):
        return redirect("staff_appointments")
    barangay = _barangay_for(request.user)
    today = timezone.localdate()

    base = Appointment.objects.filter(barangay=barangay).select_related(
        "resident", "service", "time_slot"
    )

    today_qs = base.filter(appointment_date=today).exclude(
        status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED]
    )
    pending_qs = today_qs.filter(status=Appointment.Status.PENDING).order_by(
        "time_slot__start_time", "created_at"
    )
    confirmed_qs = today_qs.filter(
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.ONGOING, Appointment.Status.COMPLETED]
    ).order_by("time_slot__start_time", "queue_number")
    upcoming_qs = base.filter(
        appointment_date__gt=today,
        status__in=ACTIVE_BOOKING_STATUSES,
    ).order_by("appointment_date", "time_slot__start_time", "queue_number")

    search = request.GET.get("q", "").strip()
    slot_id = request.GET.get("time_slot", "")
    service_id = request.GET.get("service", "")
    status_filter = request.GET.get("status", "")

    filtered_confirmed = confirmed_qs
    if search:
        filtered_confirmed = filtered_confirmed.filter(
            Q(resident__first_name__icontains=search)
            | Q(resident__last_name__icontains=search)
            | Q(service__name__icontains=search)
            | Q(sitio__icontains=search)
            | Q(queue_number__icontains=search)
        )
    if slot_id.isdigit():
        filtered_confirmed = filtered_confirmed.filter(time_slot_id=int(slot_id))
    if service_id.isdigit():
        filtered_confirmed = filtered_confirmed.filter(service_id=int(service_id))
    if status_filter in dict(Appointment.Status.choices):
        filtered_confirmed = filtered_confirmed.filter(status=status_filter)

    show_all_confirmed = request.GET.get("confirmed") == "all"
    show_all_upcoming = request.GET.get("upcoming") == "all"
    confirmed_list = list(filtered_confirmed if show_all_confirmed else filtered_confirmed[:5])
    upcoming_list = list(upcoming_qs if show_all_upcoming else upcoming_qs[:5])
    pending_list = list(pending_qs)

    for appointment in pending_list + confirmed_list + upcoming_list:
        appointment.queue_series = _queue_series(appointment.queue_number)

    return render(
        request,
        "barangay_admin/appointments.html",
        {
            "active_page": "appointments",
            "barangay": barangay,
            "today": today,
            "today_total": today_qs.count(),
            "pending_count": pending_qs.count(),
            "confirmed_count": confirmed_qs.count(),
            "upcoming_count": upcoming_qs.count(),
            "pending_appointments": pending_list,
            "confirmed_appointments": confirmed_list,
            "confirmed_total_filtered": filtered_confirmed.count(),
            "upcoming_appointments": upcoming_list,
            "show_all_confirmed": show_all_confirmed,
            "show_all_upcoming": show_all_upcoming,
            "slot_availability": _slot_availability(barangay, today),
            "services": Service.objects.filter(is_active=True).order_by("name"),
            "time_slots": TimeSlot.objects.filter(barangay=barangay, is_active=True).order_by("start_time"),
            "status_choices": [
                (Appointment.Status.CONFIRMED, "Confirmed"),
                (Appointment.Status.ONGOING, "Ongoing"),
                (Appointment.Status.COMPLETED, "Completed"),
            ],
            "filters": {
                "q": search,
                "time_slot": slot_id,
                "service": service_id,
                "status": status_filter,
            },
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )


@login_required(login_url="signin")
@require_POST
def barangay_confirm_appointment(request, pk):
    """Confirm a pending appointment for the staff member's barangay."""
    barangay = _barangay_for(request.user)
    appointment = get_object_or_404(
        Appointment.objects.select_related("resident", "service", "time_slot"),
        pk=pk,
        barangay=barangay,
    )

    if appointment.status != Appointment.Status.PENDING:
        messages.error(request, "Only pending appointments can be confirmed.")
        return redirect("barangay_appointments")

    appointment.status = Appointment.Status.CONFIRMED
    appointment.save(update_fields=["status", "updated_at"])

    Notification.objects.create(
        resident=appointment.resident,
        appointment=appointment,
        notification_type=Notification.NotificationType.APPOINTMENT_CONFIRMED,
        title="Appointment Confirmed",
        message=(
            f"Your appointment for {appointment.service.name} on "
            f"{appointment.appointment_date} "
            f"({appointment.time_slot.start_time.strftime('%I:%M %p')} - "
            f"{appointment.time_slot.end_time.strftime('%I:%M %p')}) "
            f"has been confirmed. Queue number: {appointment.queue_number}."
        ),
    )

    messages.success(
        request,
        f"Confirmed {appointment.resident} · {appointment.queue_number}.",
    )
    return redirect("barangay_appointments")
