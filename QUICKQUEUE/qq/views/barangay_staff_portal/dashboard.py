from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from qq.models import Appointment, BarangayStaff, Notification, QueueTicket


@login_required(login_url="signin")
def staff_dashboard(request):
    """Daily operational workspace for linked barangay staff accounts."""
    # Barangay-owner accounts can also have a staff record. Their ownership
    # profile takes precedence so they always remain in the admin portal.
    if hasattr(request.user, "barangay_profile"):
        return redirect("barangay_dashboard")
    try:
        staff = request.user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    if staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_dashboard")

    barangay = staff.barangay
    today = timezone.localdate()
    now = timezone.localtime()
    appointments = Appointment.objects.filter(barangay=barangay).select_related(
        "resident", "service", "time_slot"
    )
    tickets = QueueTicket.objects.filter(appointment__barangay=barangay).select_related(
        "appointment__resident", "appointment__service", "appointment__time_slot"
    )
    today_tickets = tickets.filter(appointment__appointment_date=today)
    now_serving = today_tickets.filter(status=QueueTicket.Status.NOW_SERVING).first()
    waiting_tickets = list(
        today_tickets.filter(status=QueueTicket.Status.WAITING).order_by(
            "appointment__time_slot__start_time", "queue_number"
        )[:3]
    )
    for position, ticket in enumerate(waiting_tickets):
        ticket.estimated_minutes = position * 14 if position else 0

    ready_documents = list(
        tickets.filter(claim_status=QueueTicket.ClaimStatus.READY)
        .order_by("completed_at", "updated_at")[:8]
    )
    notified_ids = set(
        Notification.objects.filter(
            appointment__queue_ticket__in=ready_documents,
        notification_type=Notification.NotificationType.QUEUE_UPDATE,
        title="Document Ready for Claiming",
        ).values_list("appointment_id", flat=True)
    )
    for ticket in ready_documents:
        ticket.resident_notified = ticket.appointment_id in notified_ids
        ready_date = (ticket.completed_at or ticket.updated_at).date()
        ticket.processing_days = max((today - ready_date).days, 1)

    upcoming = appointments.filter(
        appointment_date__gt=today,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
    ).order_by("appointment_date", "time_slot__start_time")[:3]
    notified_ready = sum(ticket.resident_notified for ticket in ready_documents)
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"

    return render(request, "barangay_staff/dashboard.html", {
        "active_page": "dashboard",
        "staff": staff,
        "barangay": barangay,
        "today": today,
        "greeting": greeting,
        "now_serving": now_serving,
        "waiting": today_tickets.filter(status=QueueTicket.Status.WAITING).count(),
        "waiting_tickets": waiting_tickets,
        "ready_documents": ready_documents,
        "ready_count": len(ready_documents),
        "notified_ready": notified_ready,
        "to_notify": len(ready_documents) - notified_ready,
        "pending_appointments": appointments.filter(status=Appointment.Status.PENDING).count(),
        "processing_documents": tickets.filter(
            claim_status=QueueTicket.ClaimStatus.PROCESSING
        ).count(),
        "upcoming_appointments": upcoming,
        "unread_notifications": Notification.objects.filter(
            appointment__barangay=barangay, admin_is_read=False
        ).count(),
    })
