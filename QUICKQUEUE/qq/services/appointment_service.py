from datetime import datetime

from django.db import transaction

from qq.models import (
    Appointment,
    QueueTicket,
    Notification,
    TimeSlot,
)
from django.utils import timezone

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

    # Lock both records: temporary-event capacity and slot capacity must remain
    # correct when residents submit concurrently.
    from qq.models import Service
    service = Service.objects.select_for_update().get(pk=service.pk)
    # remain correct even when requests arrive at nearly the same time.
    time_slot = TimeSlot.objects.select_for_update().select_related("barangay").get(pk=time_slot.pk)

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

    if not service.is_active:
        raise ValueError("This service is no longer accepting appointments.")

    if service.is_temporary:
        if service.barangay_id != resident.barangay_id:
            raise ValueError("This event is not available in your barangay.")
        if service.lifecycle == Service.Lifecycle.CANCELLED:
            raise ValueError("This event has been cancelled.")
        now = timezone.now()
        if service.end_datetime and now >= service.end_datetime:
            raise ValueError("This event has already expired.")
        if not service.start_datetime or now < service.start_datetime:
            raise ValueError("This event is not yet accepting appointments.")
        appointment_start = timezone.make_aware(
            datetime.combine(appointment_date, time_slot.start_time),
            timezone.get_current_timezone(),
        )
        if appointment_start < service.start_datetime or appointment_start >= service.end_datetime:
            raise ValueError("The selected appointment time is outside this event's schedule.")
        allowed_slots = service.available_time_slots.all()
        if allowed_slots.exists() and not allowed_slots.filter(pk=time_slot.pk).exists():
            raise ValueError("This appointment slot is no longer available.")
        if service.capacity:
            booked = Appointment.objects.filter(service=service).exclude(
                status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED]
            ).count()
            if booked >= service.capacity:
                raise ValueError("This event is fully booked.")

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
