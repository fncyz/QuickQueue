from django.db.models import Max, Q

from qq.models import Appointment, QueueTicket


CHECKED_IN_NOTE = "Resident checked in and is waiting at the barangay."


def live_queue_participation_q():
    """Waiting tickets participate only after check-in; progressed tickets stay visible."""
    return Q(notes=CHECKED_IN_NOTE) | ~Q(status=QueueTicket.Status.WAITING)


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
