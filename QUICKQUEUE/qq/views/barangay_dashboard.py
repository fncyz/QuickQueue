from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from qq.models import Appointment, Barangay, BarangayStaff, Notification, QueueTicket, Service
from qq.services.notification_service import unread_count_for_user


@login_required(login_url="signin")
def barangay_dashboard(request):
    """Dashboard overview for the barangay associated with the signed-in user."""
    try:
        barangay = request.user.barangay_profile
    except Barangay.DoesNotExist:
        try:
            staff = request.user.staff_profile
        except BarangayStaff.DoesNotExist as error:
            raise Http404("This account is not assigned to a barangay.") from error
        if staff.role != BarangayStaff.Role.ADMIN:
            return redirect("staff_dashboard")
        barangay = staff.barangay

    today = timezone.localdate()
    appointments = Appointment.objects.filter(
        barangay=barangay,
        service__is_temporary=False,
    ).select_related("service", "resident")
    today_appointments = appointments.filter(appointment_date=today)
    tickets = QueueTicket.objects.filter(
        appointment__barangay=barangay,
        appointment__appointment_date=today,
        appointment__service__is_temporary=False,
    ).select_related(
        "appointment__resident", "appointment__service"
    )
    ticket_totals = tickets.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=QueueTicket.Status.COMPLETED)),
        waiting=Count("id", filter=Q(status=QueueTicket.Status.WAITING)),
        serving=Count("id", filter=Q(status=QueueTicket.Status.NOW_SERVING)),
        missed=Count("id", filter=Q(status=QueueTicket.Status.MISSED)),
        cancelled=Count("id", filter=Q(status=QueueTicket.Status.CANCELLED)),
    )
    completed = ticket_totals["completed"]
    waiting = ticket_totals["waiting"]
    serving_count = ticket_totals["serving"]
    now_serving = tickets.filter(status=QueueTicket.Status.NOW_SERVING).first()
    no_show = ticket_totals["missed"]
    cancelled = ticket_totals["cancelled"]
    total_tickets = ticket_totals["total"]

    month_start = today.replace(day=1)
    month_appointments = appointments.filter(appointment_date__gte=month_start, appointment_date__lte=today)
    month_total = month_appointments.count()
    month_tickets = QueueTicket.objects.filter(
        appointment__barangay=barangay,
        appointment__service__is_temporary=False,
        appointment__appointment_date__gte=month_start,
        appointment__appointment_date__lte=today,
    )
    month_ticket_totals = month_tickets.aggregate(
        completed=Count("id", filter=Q(status=QueueTicket.Status.COMPLETED)),
        cancelled=Count(
            "id",
            filter=Q(status__in=[QueueTicket.Status.CANCELLED, QueueTicket.Status.MISSED]),
        ),
    )
    month_completed = month_ticket_totals["completed"]
    month_cancelled = month_ticket_totals["cancelled"]

    def service_breakdown(queryset):
        return list(queryset.values("service__name").annotate(count=Count("id")).order_by("-count", "service__name"))

    special_service_records = (
        Service.objects.filter(
            is_temporary=True,
            barangay=barangay,
            is_active=True,
            lifecycle=Service.Lifecycle.SCHEDULED,
            event_end_date__gte=today,
        )
        .annotate(
            dashboard_booking_count=Count(
                "appointments",
                filter=Q(appointments__barangay=barangay)
                & ~Q(appointments__status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED]),
                distinct=True,
            )
        )
        .order_by("event_start_date", "name")
    )
    special_services = []
    status_labels = {
        "upcoming": "Upcoming",
        "active": "Registration Open",
        "ending_soon": "Registration Ending Soon",
        "fully_booked": "Fully Booked",
        "booking_closed": "Registration Closed",
    }
    for service in special_service_records:
        display_status = service.computed_status(
            booking_count=service.dashboard_booking_count
        )
        if display_status in {"expired", "cancelled", "deactivated", "archived"}:
            continue
        service.dashboard_status = status_labels.get(display_status, service.get_lifecycle_display())
        service.dashboard_status_code = display_status
        service.remaining_capacity = (
            max(service.capacity - service.dashboard_booking_count, 0)
            if service.capacity is not None else None
        )
        special_services.append(service)
    regular_services = service_breakdown(month_appointments.filter(service__is_temporary=False))
    max_regular_service_count = max((item["count"] for item in regular_services), default=1)

    running_total = 0
    queue_chart = {}
    for key, value in (("completed", completed), ("serving", serving_count),
                       ("waiting", waiting), ("no_show", no_show), ("cancelled", cancelled)):
        running_total += value
        queue_chart[f"{key}_end"] = round((running_total / total_tickets) * 100) if total_tickets else 0

    return render(request, "barangay_admin/dashboard.html", {
        "active_page": "dashboard",
        "barangay": barangay,
        "today": today,
        "today_total": today_appointments.count(),
        "completed": completed,
        "waiting": waiting,
        "serving_count": serving_count,
        "now_serving": now_serving,
        "recent_tickets": tickets.order_by("-updated_at")[:5],
        "total_tickets": total_tickets,
        "no_show": no_show,
        "cancelled": cancelled,
        "queue_chart": queue_chart,
        "special_services": special_services,
        "regular_services": regular_services,
        "max_regular_service_count": max_regular_service_count,
        "registered_residents": barangay.residents.count(),
        "month_total": month_total,
        "month_completed": month_completed,
        "month_cancelled": month_cancelled,
        "unread_notifications": unread_count_for_user(request.user),
    })
