from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Appointment, QueueTicket


ACTIVE_APPOINTMENT_STATUSES = [
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
    Appointment.Status.ONGOING,
]


@login_required(login_url="signin")
def resident_queue_status(request):
    """Show live queue information for the resident's next active appointment."""
    resident = request.user.resident_profile
    appointment = (
        resident.appointments.select_related(
            "service", "barangay", "time_slot"
        )
        .filter(appointment_date__gte=date.today(), status__in=ACTIVE_APPOINTMENT_STATUSES)
        .order_by("appointment_date", "time_slot__start_time")
        .first()
    )

    context = {"active_page": "queue", "appointment": appointment}
    if not appointment:
        return render(request, "resident/queue_status.html", context)

    queue = QueueTicket.objects.filter(
        appointment__appointment_date=appointment.appointment_date,
        appointment__barangay=appointment.barangay,
        appointment__service=appointment.service,
    ).select_related("appointment")
    now_serving = queue.filter(status=QueueTicket.Status.NOW_SERVING).first()
    ahead = queue.filter(
        status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.NOW_SERVING],
        appointment__queue_number__lt=appointment.queue_number,
    ).count()
    context.update(
        {
            "ticket": QueueTicket.objects.filter(appointment=appointment).first(),
            "now_serving": now_serving,
            "people_ahead": ahead,
            "estimated_wait": ahead * appointment.service.estimated_duration,
        }
    )
    return render(request, "resident/queue_status.html", context)


@login_required(login_url="signin")
@require_POST
def resident_check_in(request, pk):
    """Check in a resident only when their confirmed appointment has started."""
    resident = request.user.resident_profile
    appointment = get_object_or_404(
        Appointment.objects.select_related("time_slot"),
        pk=pk,
        resident=resident,
    )
    today = timezone.localdate()

    if appointment.appointment_date > today:
        messages.error(
            request,
            "You are too early to check in. Your appointment is on "
            f"{appointment.appointment_date.strftime('%B %d, %Y')}.",
        )
        return redirect("resident_queue_status")

    if appointment.appointment_date < today:
        messages.error(request, "Check-in is no longer available for this appointment.")
        return redirect("resident_queue_status")

    if appointment.status not in (Appointment.Status.CONFIRMED, Appointment.Status.ONGOING):
        messages.error(request, "Your appointment must be confirmed before you can check in.")
        return redirect("resident_queue_status")

    current_time = timezone.localtime().time().replace(tzinfo=None)
    if current_time < appointment.time_slot.start_time:
        messages.error(
            request,
            "You are too early to check in. Check-in will be available at "
            f"{appointment.time_slot.start_time.strftime('%I:%M %p')}.",
        )
        return redirect("resident_queue_status")

    ticket = QueueTicket.objects.filter(appointment=appointment).first()
    if not ticket:
        messages.error(request, "Your queue ticket is not available. Please contact barangay staff.")
        return redirect("resident_queue_status")

    ticket.notes = "Resident checked in and is waiting at the barangay."
    ticket.save(update_fields=["notes", "updated_at"])
    messages.success(request, "You are checked in. Barangay staff have been notified.")
    return redirect("resident_queue_status")


@login_required(login_url="signin")
@require_POST
def resident_cancel_appointment(request, pk):
    """Cancel a pending or confirmed appointment owned by the signed-in resident."""
    resident = request.user.resident_profile

    with transaction.atomic():
        appointment = get_object_or_404(
            Appointment.objects.select_for_update(),
            pk=pk,
            resident=resident,
        )
        if appointment.status not in (
            Appointment.Status.PENDING,
            Appointment.Status.CONFIRMED,
        ):
            messages.error(request, "This appointment can no longer be cancelled.")
            return redirect("resident_queue_status")

        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        QueueTicket.objects.filter(appointment=appointment).update(
            status=QueueTicket.Status.CANCELLED,
            updated_at=timezone.now(),
        )

    messages.success(request, "Your appointment has been cancelled.")
    return redirect("resident_queue_status")
