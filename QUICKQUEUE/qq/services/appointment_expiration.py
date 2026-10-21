from datetime import datetime

from django.db import transaction
from django.utils import timezone

from qq.models import Appointment, QueueTicket
from qq.services.queue_service import CHECKED_IN_NOTE


EXPIRABLE_APPOINTMENT_STATUSES = (
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
)


def appointment_start_at(appointment):
    """Return the aware local start instant for a regular appointment."""
    if not appointment.appointment_date or not appointment.time_slot:
        return None
    local_start = datetime.combine(
        appointment.appointment_date,
        appointment.time_slot.start_time,
    )
    return timezone.make_aware(local_start, timezone.get_default_timezone())


def appointment_expiration_at(appointment):
    """Return the aware local instant at which a regular appointment expires."""
    if not appointment.appointment_date or not appointment.time_slot:
        return None
    local_end = datetime.combine(appointment.appointment_date, appointment.time_slot.end_time)
    return timezone.make_aware(local_end, timezone.get_default_timezone())


def appointment_checkin_window_open(appointment, *, at=None):
    """Check in is allowed from scheduled start up to, but not including, end."""
    start_at = appointment_start_at(appointment)
    end_at = appointment_expiration_at(appointment)
    if start_at is None or end_at is None:
        return False
    at = at or timezone.now()
    return start_at <= at < end_at


def is_appointment_expired(appointment, *, at=None, ticket=None):
    """Check expiry while preserving appointments that have entered processing."""
    if appointment.status not in EXPIRABLE_APPOINTMENT_STATUSES:
        return False
    expiration_at = appointment_expiration_at(appointment)
    if expiration_at is None:
        return False
    at = at or timezone.now()
    if at < expiration_at:
        return False
    if ticket is None:
        try:
            ticket = appointment.queue_ticket
        except QueueTicket.DoesNotExist:
            return True
    return (
        ticket.status == QueueTicket.Status.WAITING
        and ticket.claim_status == QueueTicket.ClaimStatus.NONE
        and ticket.notes != CHECKED_IN_NOTE
    )


def is_recorded_appointment_expiration(appointment, *, at=None, ticket=None):
    """Identify persisted slot expiry without relabeling queue no-shows."""
    if appointment.status != Appointment.Status.MISSED:
        return False
    expiration_at = appointment_expiration_at(appointment)
    at = at or timezone.now()
    if expiration_at is None or at < expiration_at:
        return False
    if ticket is None:
        try:
            ticket = appointment.queue_ticket
        except QueueTicket.DoesNotExist:
            return True
    return (
        ticket.status == QueueTicket.Status.MISSED
        and ticket.claim_status == QueueTicket.ClaimStatus.NONE
        and ticket.notes != CHECKED_IN_NOTE
        and ticket.notes != "Resident did not show up"
    )


def expire_overdue_appointments(*, at=None, barangay=None, resident=None):
    """Mark eligible appointments missed once their actual slot end has passed.

    This is request-triggered because QuickQueue has no configured periodic task
    runner. Call it from resident, staff, and queue entry points.
    """
    at = at or timezone.now()
    local_today = timezone.localdate(at)
    candidates = Appointment.objects.filter(
        status__in=EXPIRABLE_APPOINTMENT_STATUSES,
        appointment_date__lte=local_today,
        time_slot__isnull=False,
        service__is_temporary=False,
    )
    if barangay is not None:
        candidates = candidates.filter(barangay=barangay)
    if resident is not None:
        candidates = candidates.filter(resident=resident)

    expired = 0
    for appointment_id in candidates.values_list("pk", flat=True).iterator():
        with transaction.atomic():
            appointment = Appointment.objects.select_for_update(of=("self",)).select_related(
                "time_slot"
            ).get(pk=appointment_id)
            ticket = QueueTicket.objects.select_for_update().filter(
                appointment_id=appointment_id
            ).first()
            if not is_appointment_expired(appointment, at=at, ticket=ticket):
                continue
            appointment.status = Appointment.Status.MISSED
            appointment.save(update_fields=["status", "updated_at"])
            if ticket is not None:
                ticket.status = QueueTicket.Status.MISSED
                ticket.save(update_fields=["status", "updated_at"])
            expired += 1
    return expired
