from django.contrib.auth.decorators import login_required
from django.db.models import Avg, DurationField, ExpressionWrapper, F
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from qq.models import BarangayStaff, Notification, QueueTicket, Service
from qq.views.barangay_live_queue import (
    _annotate_wait_estimates, _resolve_slot, _ticket_queryset, _window_label,
)


@login_required(login_url="signin")
def staff_live_queue(request):
    try:
        staff = request.user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_live_queue")

    barangay = staff.barangay
    today, now = timezone.localdate(), timezone.localtime()
    current_slot, slots = _resolve_slot(barangay, request.GET.get("slot"), today, now.time())
    tickets, now_serving, next_in_line = [], None, []
    waiting_count = completed_count = serving_count = 0
    next_wait_minutes, window = None, "A"
    if current_slot:
        window = _window_label(slots, current_slot)
        tickets = _annotate_wait_estimates(list(_ticket_queryset(barangay, today, current_slot)))
        now_serving = next((t for t in tickets if t.status == QueueTicket.Status.NOW_SERVING), None)
        waiting_count = sum(t.status == QueueTicket.Status.WAITING for t in tickets)
        completed_count = sum(t.status == QueueTicket.Status.COMPLETED for t in tickets)
        serving_count = sum(t.status == QueueTicket.Status.NOW_SERVING for t in tickets)
        next_in_line = [t for t in tickets if t.status == QueueTicket.Status.WAITING][:3]
        if next_in_line:
            next_wait_minutes = next_in_line[0].wait_minutes

    today_tickets = QueueTicket.objects.filter(
        appointment__barangay=barangay, appointment__appointment_date=today
    ).exclude(status=QueueTicket.Status.CANCELLED)
    completed_today = today_tickets.filter(status=QueueTicket.Status.COMPLETED)
    avg_duration = completed_today.exclude(called_at=None).exclude(completed_at=None).annotate(
        service_seconds=ExpressionWrapper(F("completed_at") - F("called_at"), output_field=DurationField())
    ).aggregate(avg=Avg("service_seconds"))["avg"]
    if avg_duration:
        average_minutes = round(avg_duration.total_seconds() / 60, 1)
    else:
        service_avg = Service.objects.filter(is_active=True).aggregate(avg=Avg("estimated_duration"))["avg"]
        average_minutes = round(service_avg, 1) if service_avg else 0
    current_index = slots.index(current_slot) if current_slot in slots else -1
    next_slot = slots[current_index + 1] if 0 <= current_index < len(slots) - 1 else None
    return render(request, "barangay_staff/live_queue.html", {
        "active_page": "queue", "staff": staff, "barangay": barangay, "today": today,
        "current_slot": current_slot, "slots": slots, "window_label": window, "tickets": tickets,
        "now_serving": now_serving, "waiting_count": waiting_count,
        "completed_count": completed_count, "serving_count": serving_count,
        "slot_capacity": current_slot.max_appointments if current_slot else 0,
        "next_in_line": next_in_line, "next_wait_minutes": next_wait_minutes, "next_slot": next_slot,
        "services": Service.objects.filter(is_active=True).order_by("name"),
        "stats": {"average_service_minutes": average_minutes, "completed_today": completed_today.count(),
                  "waiting_today": today_tickets.filter(status=QueueTicket.Status.WAITING).count(),
                  "total_today": today_tickets.count()},
        "unread_notifications": Notification.objects.filter(
            appointment__barangay=barangay, admin_is_read=False
        ).count(),
    })
