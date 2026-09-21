from django.db.models import Max

from qq.models import Appointment


def generate_queue_number(
    barangay,
    service,
    appointment_date,
):
    """
    Generate the next queue number for a service
    on a specific date.

    Example:
        BC-001
        BC-002
        BC-003
    """

    service_code = service.code or "SRV"

    latest = (
        Appointment.objects.filter(
            barangay=barangay,
            service=service,
            appointment_date=appointment_date,
        )
        .aggregate(Max("queue_number"))
    )

    latest_queue = latest["queue_number__max"]

    if latest_queue is None:
        number = 1
    else:
        number = int(latest_queue.split("-")[1]) + 1

    return f"{service_code}-{number:03d}"
