from django.db import transaction

from qq.models import (
    Appointment,
    QueueTicket,
    Notification,
)

from .queue_service import generate_queue_number


def check_duplicate_appointment(
    resident,
    appointment_date,
    time_slot,
):
    """
    Returns True if the resident already has
    an appointment for the selected date and time.
    """

    return Appointment.objects.filter(
        resident=resident,
        appointment_date=appointment_date,
        time_slot=time_slot,
    ).exists()


def check_timeslot_capacity(
    appointment_date,
    time_slot,
):
    """
    Returns True if the selected time slot
    still has available capacity.
    """

    booked = Appointment.objects.filter(
        appointment_date=appointment_date,
        time_slot=time_slot,
    ).count()

    return booked < time_slot.max_appointments


@transaction.atomic
def create_appointment(
    resident,
    service,
    appointment_date,
    time_slot,
    purpose,
    sitio="",
):
    """
    Creates an appointment together with its
    queue ticket and notification.
    """

    if check_duplicate_appointment(
        resident,
        appointment_date,
        time_slot,
    ):
        raise ValueError(
            "You already have an appointment for this time slot."
        )

    if time_slot.barangay != resident.barangay:
        raise ValueError(
            "Invalid time slot selected."
        )

    if not check_timeslot_capacity(
        appointment_date,
        time_slot,
    ):
        raise ValueError(
            "This time slot is already full."
        )

    queue_number = generate_queue_number(
        resident.barangay,
        service,
        appointment_date,
    )

    appointment = Appointment.objects.create(
        resident=resident,
        barangay=resident.barangay,
        service=service,
        appointment_date=appointment_date,
        time_slot=time_slot,
        purpose=purpose,
        sitio=sitio,
        queue_number=queue_number,
    )

    QueueTicket.objects.create(
        appointment=appointment,
        queue_number=queue_number,
    )

    Notification.objects.create(
        resident=resident,
        appointment=appointment,
        notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
        title="Appointment Submitted",
        message=(
            f"Your appointment request has been submitted and is awaiting staff confirmation.\n"
            f"Queue Number: {queue_number}\n"
            f"Date: {appointment_date}\n"
            f"Time: {time_slot.start_time} - {time_slot.end_time}"
        ),
    )

    return appointment
