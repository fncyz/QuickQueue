from django.db import transaction

from qq.models import (
    Appointment,
    QueueTicket,
    Notification,
    TimeSlot,
    EventBooking,
    BarangayServiceConfiguration,
    ClosedAppointmentDate,
    Barangay,
)
from django.utils import timezone

from .queue_service import generate_queue_number
from .timeslot_service import regular_daily_capacity, regular_slot_capacities
from .notification_service import notify_barangay_staff, notify_resident


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
    ).exclude(status=Appointment.Status.CANCELLED).exists()


def check_timeslot_capacity(
    appointment_date,
    time_slot,
    capacity=None,
):
    """
    Returns True if the selected time slot
    still has available capacity.
    """

    booked = Appointment.objects.filter(
        appointment_date=appointment_date,
        time_slot=time_slot,
        service__is_temporary=False,
    ).exclude(status=Appointment.Status.CANCELLED).count()

    if capacity is None:
        capacity = regular_slot_capacities(time_slot.barangay).get(time_slot.pk, 0)
    return booked < capacity


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

    # Lock the barangay capacity and every shared regular slot so per-slot and
    # daily checks are serialized across all regular services.
    from qq.models import Service
    barangay = Barangay.objects.select_for_update().get(pk=resident.barangay_id)
    service = Service.objects.select_for_update().get(pk=service.pk)
    if service.is_temporary:
        raise ValueError("Special Services must be reserved through the event booking flow.")
    service_configuration, _ = BarangayServiceConfiguration.objects.select_for_update().get_or_create(
        barangay=barangay,
        service=service,
        defaults={"estimated_duration": service.estimated_duration},
    )
    locked_slots = list(TimeSlot.objects.select_for_update().select_related("barangay").filter(
        barangay=barangay,
        is_active=True,
    ).order_by("pk"))
    time_slot = next((slot for slot in locked_slots if slot.pk == time_slot.pk), None)
    if time_slot is None:
        raise ValueError("Invalid time slot selected.")
    slot_capacities = regular_slot_capacities(barangay, locked_slots)

    now = timezone.localtime()
    today = timezone.localdate(now)
    if appointment_date < today:
        raise ValueError("Past appointment dates are closed.")
    closed_date = ClosedAppointmentDate.objects.filter(
        barangay=resident.barangay,
        date=appointment_date,
    ).first()
    if closed_date:
        reason = f" Reason: {closed_date.reason}" if closed_date.reason else ""
        raise ValueError(f"Appointments are unavailable on this date.{reason}")
    if appointment_date.weekday() >= 5:
        raise ValueError("Regular appointments are available Monday through Friday only.")
    if appointment_date == today and now.time() >= time_slot.start_time:
        raise ValueError("Booking for this time slot has closed.")

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

    if not service.is_active or not service_configuration.is_active:
        raise ValueError("This service is no longer accepting appointments.")

    if not check_timeslot_capacity(
        appointment_date,
        time_slot,
        slot_capacities.get(time_slot.pk, 0),
    ):
        raise ValueError(
            "This time slot is already fully booked. Please select another available time."
        )

    daily_booked = Appointment.objects.filter(
        barangay=barangay,
        appointment_date=appointment_date,
        time_slot__isnull=False,
        service__is_temporary=False,
    ).exclude(status=Appointment.Status.CANCELLED).count()
    if daily_booked >= regular_daily_capacity(barangay):
        raise ValueError("This appointment date is already fully booked. Please select another available date.")

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
        status=Appointment.Status.CONFIRMED,
        service_fee_snapshot=service_configuration.fee,
    )

    QueueTicket.objects.create(
        appointment=appointment,
        queue_number=queue_number,
    )
    notify_resident(
        appointment=appointment,
        notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
        title="Appointment Confirmed",
        message=(
            "Your appointment has been confirmed.\n" +
            f"Queue Number: {queue_number}\n"
            f"Date: {appointment_date}\n"
            f"Time: {time_slot.start_time} - {time_slot.end_time}"
        ), event_key=f"appointment:{appointment.pk}:created",
    )
    notify_barangay_staff(
        appointment=appointment,
        title="New Appointment",
        message=f"{resident} booked {service.name} for {appointment_date}.",
        event_key=f"appointment:{appointment.pk}:staff-created",
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
    if not service.event_end_date or today > service.event_end_date:
        raise ValueError("This Special Service has expired.")
    if not service.booking_start_date or today < service.booking_start_date:
        raise ValueError("Booking for this Special Service is not yet open.")
    if not service.booking_end_date or today > service.booking_end_date:
        raise ValueError("Booking for this Special Service has closed.")

    if Appointment.objects.filter(resident=resident, service=service).exclude(
        status=Appointment.Status.CANCELLED
    ).exists():
        raise ValueError("You already have a booking for this Special Service.")

    booked = Appointment.objects.filter(service=service).exclude(
        status=Appointment.Status.CANCELLED
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
    notify_resident(
        appointment=appointment,
        notification_type=Notification.NotificationType.EVENT_UPDATE,
        title="Special Service Booking Confirmed",
        message=(
            f"Your reservation for {service.name} is confirmed.\n"
            f"Booking Reference: {event_booking.booking_reference}\n"
            f"Event Date: {event_date}\n"
            "Open your QR Pass and present it at the venue."
        ), event_key=f"event-booking:{event_booking.pk}:confirmed",
    )
    notify_barangay_staff(
        appointment=appointment,
        title="New Special Service Booking",
        message=f"{resident} booked {service.name}. Reference: {event_booking.booking_reference}.",
        event_key=f"event-booking:{event_booking.pk}:staff-created",
    )
    return appointment
