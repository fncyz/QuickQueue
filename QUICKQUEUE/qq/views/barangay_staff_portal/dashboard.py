from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Appointment, BarangayStaff, QueueTicket, Service


def _staff_for_dashboard(user):
    if hasattr(user, "barangay_profile"):
        return None
    try:
        return user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error


@login_required(login_url="signin")
def staff_dashboard(request):
    """Daily operational workspace for linked barangay staff accounts."""
    # Barangay-owner accounts can also have a staff record. Their ownership
    # profile takes precedence so they always remain in the admin portal.
    staff = _staff_for_dashboard(request.user)
    if staff is None:
        return redirect("barangay_dashboard")
    if staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_dashboard")

    barangay = staff.barangay
    today = timezone.localdate()
    now = timezone.localtime()
    appointments = Appointment.objects.filter(
        barangay=barangay, service__is_temporary=False,
    ).select_related(
        "resident", "service", "time_slot"
    )
    tickets = QueueTicket.objects.filter(
        appointment__barangay=barangay,
        appointment__service__is_temporary=False,
    ).select_related(
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

    ready_documents_query = tickets.filter(claim_status=QueueTicket.ClaimStatus.READY)
    ready_count = ready_documents_query.count()
    ready_documents = list(ready_documents_query.order_by("-updated_at")[:6])
    for ticket in ready_documents:
        ready_date = (ticket.completed_at or ticket.updated_at).date()
        ticket.processing_days = max((today - ready_date).days, 1)

    upcoming = appointments.filter(
        appointment_date__gt=today,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
    ).order_by("appointment_date", "time_slot__start_time")[:3]
    event_services = list(
        Service.objects.filter(
            barangay=barangay,
            is_temporary=True,
            is_active=True,
            lifecycle=Service.Lifecycle.SCHEDULED,
            event_end_date__gte=today,
        )
        .annotate(
            dashboard_booking_count=Count(
                "appointments",
                filter=~Q(
                    appointments__status__in=[
                        Appointment.Status.CANCELLED,
                        Appointment.Status.MISSED,
                    ]
                ),
                distinct=True,
            )
        )
        .order_by("event_start_date", "name")[:4]
    )
    status_labels = {
        "upcoming": "Upcoming",
        "active": "Active",
        "ending_soon": "Ending Soon",
        "fully_booked": "Fully Booked",
        "booking_closed": "Booking Closed",
    }
    for offering in event_services:
        offering.display_status = offering.computed_status(
            now, offering.dashboard_booking_count
        )
        offering.dashboard_status = status_labels.get(
            offering.display_status, offering.get_lifecycle_display()
        )
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
        "ready_count": ready_count,
        "pending_appointments": appointments.filter(status=Appointment.Status.PENDING).count(),
        "processing_documents": tickets.filter(
            claim_status=QueueTicket.ClaimStatus.PROCESSING
        ).count(),
        "upcoming_appointments": upcoming,
        "event_services": event_services,
    })


@login_required(login_url="signin")
@require_POST
def staff_dashboard_mark_claimed(request, pk):
    staff = _staff_for_dashboard(request.user)
    if staff is None or staff.role == BarangayStaff.Role.ADMIN:
        raise Http404("This action is available to barangay staff accounts only.")
    with transaction.atomic():
        ticket = get_object_or_404(
            QueueTicket.objects.select_for_update(),
            pk=pk,
            appointment__barangay=staff.barangay,
            appointment__service__is_temporary=False,
        )
        if ticket.claim_status != QueueTicket.ClaimStatus.READY:
            messages.error(request, "Only documents that are ready for pickup can be marked as claimed.")
            return redirect("staff_dashboard")
        ticket.claim_status = QueueTicket.ClaimStatus.CLAIMED
        ticket.claimed_at = timezone.now()
        ticket.save(update_fields=["claim_status", "claimed_at", "updated_at"])
    messages.success(request, f"{ticket.queue_number} was marked as claimed.")
    return redirect("staff_dashboard")
