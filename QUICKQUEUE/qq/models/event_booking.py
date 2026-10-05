import uuid

from django.conf import settings
from django.core import signing
from django.db import models

from .appointment import Appointment


class EventBooking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        CANCELLED = "cancelled", "Cancelled"

    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="event_booking"
    )
    booking_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="event_checkins",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def booking_reference(self):
        return f"EVT-{self.booking_id.hex[:8].upper()}"

    def qr_token(self):
        return signing.dumps(
            {"event_booking": str(self.booking_id)},
            salt="quickqueue.event-booking-pass",
            compress=True,
        )

    @classmethod
    def booking_id_from_token(cls, token):
        payload = signing.loads(token, salt="quickqueue.event-booking-pass")
        return uuid.UUID(payload["event_booking"])

    def __str__(self):
        return self.booking_reference
