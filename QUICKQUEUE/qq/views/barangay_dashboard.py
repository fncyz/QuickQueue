from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from qq.models import Appointment, Barangay, BarangayStaff, QueueTicket


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
    appointments = Appointment.objects.filter(barangay=barangay).select_related("service", "resident")
    today_appointments = appointments.filter(appointment_date=today)
    tickets = QueueTicket.objects.filter(appointment__barangay=barangay, appointment__appointment_date=today).select_related(
        "appointment__resident", "appointment__service"
    )
    completed = tickets.filter(status=QueueTicket.Status.COMPLETED).count()
    waiting = tickets.filter(status=QueueTicket.Status.WAITING).count()
    serving_count = tickets.filter(status=QueueTicket.Status.NOW_SERVING).count()
    now_serving = tickets.filter(status=QueueTicket.Status.NOW_SERVING).first()
    no_show = tickets.filter(status=QueueTicket.Status.MISSED).count()
    cancelled = tickets.filter(status=QueueTicket.Status.CANCELLED).count()
    total_tickets = tickets.count()

    month_start = today.replace(day=1)
    month_appointments = appointments.filter(appointment_date__gte=month_start, appointment_date__lte=today)
    month_total = month_appointments.count()
    month_tickets = QueueTicket.objects.filter(
        appointment__barangay=barangay,
        appointment__appointment_date__gte=month_start,
        appointment__appointment_date__lte=today,
    )
    month_completed = month_tickets.filter(status=QueueTicket.Status.COMPLETED).count()
    month_cancelled = month_tickets.filter(
        status__in=[QueueTicket.Status.CANCELLED, QueueTicket.Status.MISSED]
    ).count()

    def service_breakdown(queryset):
        return list(queryset.values("service__name").annotate(count=Count("id")).order_by("-count", "service__name"))

    today_services = service_breakdown(today_appointments)
    month_services = service_breakdown(month_appointments)
    max_today_service_count = max((item["count"] for item in today_services), default=1)
    max_month_service_count = max((item["count"] for item in month_services), default=1)

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
        "today_services": today_services,
        "month_services": month_services,
        "max_today_service_count": max_today_service_count,
        "max_month_service_count": max_month_service_count,
        "registered_residents": barangay.residents.count(),
        "month_total": month_total,
        "month_completed": month_completed,
        "month_cancelled": month_cancelled,
    })
