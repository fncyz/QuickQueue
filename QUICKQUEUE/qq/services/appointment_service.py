from django.db import transaction

from qq.models import (
    Appointment,
    QueueTicket,
    Notification,
    TimeSlot,
    EventBooking,
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

    # Lock both records so normal appointment slot capacity remains correct
    # when residents submit concurrently.
    from qq.models import Service
    service = Service.objects.select_for_update().get(pk=service.pk)
    if service.is_temporary:
        raise ValueError("Special Services must be reserved through the event booking flow.")
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
            "Your appointment request has been submitted and is awaiting staff confirmation.\n" +
            f"Queue Number: {queue_number}\n"
            f"Date: {appointment_date}\n"
            f"Time: {time_slot.start_time} - {time_slot.end_time}"
        ),
    )

    return appointment


@transaction.atomic
def create_special_service_booking(resident, service):
    """Reserve one capacity slot without creating a queue or time-slot booking."""
    from qq.models import Service

    service = Service.objects.select_for_update().get(pk=service.pk)
    if not service.is_temporary:
        raise ValueError("This service uses the regular appointment booking flow.")
    if service.barangay_id != resident.barangay_id:
        raise ValueError("This Special Service is not available in your barangay.")
    if not service.is_active or service.lifecycle == Service.Lifecycle.CANCELLED:
        raise ValueError("This Special Service is no longer accepting bookings.")

    today = timezone.localdate()
    if not service.booking_start_date or today < service.booking_start_date:
        raise ValueError("Booking for this Special Service is not yet open.")
    if not service.booking_end_date or today > service.booking_end_date:
        raise ValueError("Booking for this Special Service has closed.")

    if Appointment.objects.filter(resident=resident, service=service).exclude(
        status=Appointment.Status.CANCELLED
    ).exists():
        raise ValueError("You already have a booking for this Special Service.")

    booked = Appointment.objects.filter(service=service).exclude(
        status__in=[Appointment.Status.CANCELLED, Appointment.Status.MISSED]
    ).count()
    if not service.capacity or booked >= service.capacity:
        raise ValueError("This Special Service is fully booked.")

    appointment = Appointment.objects.create(
        resident=resident,
        barangay=resident.barangay,
        service=service,
        appointment_date=service.event_start_date,
        time_slot=None,
        purpose="",
        sitio="",
        queue_number="",
        status=Appointment.Status.CONFIRMED,
    )
    event_booking = EventBooking.objects.create(appointment=appointment)
    event_date = service.event_start_date.strftime("%B %d, %Y")
    if service.event_end_date and service.event_end_date != service.event_start_date:
        event_date += f" - {service.event_end_date.strftime('%B %d, %Y')}"
    Notification.objects.create(
        resident=resident,
        appointment=appointment,
        notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
        title="Special Service Booking Confirmed",
        message=(
            f"Your reservation for {service.name} is confirmed.\n"
            f"Booking Reference: {event_booking.booking_reference}\n"
            f"Event Date: {event_date}\n"
            "Open your QR Pass and present it at the venue."
        ),
    )
    return appointment
