from django.db.models import Max, Q
from django.utils import timezone

from qq.models import Appointment, QueueTicket


CHECKED_IN_NOTE = "Resident checked in and is waiting at the barangay."


def finalized_queue_q():
    """Authoritative predicate for a fully finalized resident transaction."""
    return Q(
        claim_status=QueueTicket.ClaimStatus.CLAIMED,
        appointment__status=Appointment.Status.COMPLETED,
    )


def active_queue_status_q(status):
    """Match an active raw queue status without finalized/terminal records."""
    return (
        Q(status=status)
        & ~Q(claim_status=QueueTicket.ClaimStatus.CLAIMED)
        & ~Q(
            appointment__status__in=[
                Appointment.Status.COMPLETED,
                Appointment.Status.CANCELLED,
                Appointment.Status.MISSED,
            ]
        )
    )


def cancelled_queue_q():
    return (
        Q(appointment__status=Appointment.Status.CANCELLED)
        | (
            Q(status=QueueTicket.Status.CANCELLED)
            & ~Q(appointment__status=Appointment.Status.MISSED)
        )
    ) & ~finalized_queue_q()


def missed_queue_q():
    return (
        Q(appointment__status=Appointment.Status.MISSED)
        | (
            Q(status=QueueTicket.Status.MISSED)
            & ~Q(appointment__status=Appointment.Status.CANCELLED)
        )
    ) & ~finalized_queue_q()


def live_queue_participation_q():
    """Waiting tickets participate only after check-in; progressed tickets stay visible."""
    return (
        (Q(notes=CHECKED_IN_NOTE) | ~Q(status=QueueTicket.Status.WAITING))
        & ~Q(claim_status=QueueTicket.ClaimStatus.CLAIMED)
    )


def mark_document_claimed(ticket, *, claimed_at=None):
    """Apply the terminal document-claim transition to a locked queue ticket.

    Callers must obtain the ticket with ``select_for_update()`` inside an atomic
    transaction. Ready for Pickup remains non-terminal; only an actual claim
    closes any lingering active queue/appointment state.
    """
    if ticket.claim_status == QueueTicket.ClaimStatus.CLAIMED:
        return False
    if ticket.claim_status != QueueTicket.ClaimStatus.READY:
        raise ValueError("Only documents that are ready for pickup can be marked as claimed.")

    now = claimed_at or timezone.now()
    ticket.claim_status = QueueTicket.ClaimStatus.CLAIMED
    ticket.claimed_at = now
    update_fields = ["claim_status", "claimed_at", "updated_at"]
    if ticket.status not in (
        QueueTicket.Status.COMPLETED,
        QueueTicket.Status.MISSED,
        QueueTicket.Status.CANCELLED,
    ):
        ticket.status = QueueTicket.Status.COMPLETED
        ticket.completed_at = ticket.completed_at or now
        update_fields.extend(["status", "completed_at"])
    ticket.save(update_fields=update_fields)

    appointment = ticket.appointment
    if appointment.status not in (
        Appointment.Status.COMPLETED,
        Appointment.Status.CANCELLED,
        Appointment.Status.MISSED,
    ):
        appointment.status = Appointment.Status.COMPLETED
        appointment.save(update_fields=["status", "updated_at"])
    return True


def generate_queue_number(barangay, service, appointment_date):
    """Generate the next queue number for a service on a specific date."""
    service_code = service.code or "SRV"
    latest_queue = (
        Appointment.objects.filter(
            barangay=barangay,
            service=service,
            appointment_date=appointment_date,
        )
        .aggregate(Max("queue_number"))["queue_number__max"]
    )
    number = 1 if latest_queue is None else int(latest_queue.split("-")[1]) + 1
    return f"{service_code}-{number:03d}"
