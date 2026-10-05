from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Service(models.Model):
    class TemporaryType(models.TextChoices):
        EVENT = "event", "Event"
        SERVICE = "temporary_service", "Temporary Service"

    class Lifecycle(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CANCELLED = "cancelled", "Cancelled"
    code = models.CharField(
        max_length=5,
        blank=True,
        default="",
        help_text="Short service code used in queue numbers."
    )
    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField()

    requirements = models.TextField(
        blank=True,
        help_text="Requirements needed for this service."
    )

    estimated_duration = models.PositiveIntegerField(
        help_text="Estimated processing time in minutes."
    )

    is_active = models.BooleanField(
        default=True
    )

    # Permanent services leave these fields empty. Temporary offerings retain
    # the same Service identity so appointment and transaction history is never
    # detached when the offering expires or is cancelled.
    is_temporary = models.BooleanField(default=False)
    temporary_type = models.CharField(max_length=20, choices=TemporaryType.choices, blank=True)
    barangay = models.ForeignKey(
        "Barangay", on_delete=models.PROTECT, related_name="temporary_services",
        null=True, blank=True,
    )
    location = models.CharField(max_length=200, blank=True)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    slot_duration = models.PositiveIntegerField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    lifecycle = models.CharField(max_length=12, choices=Lifecycle.choices, default=Lifecycle.SCHEDULED)
    available_time_slots = models.ManyToManyField("TimeSlot", blank=True, related_name="temporary_services")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_temporary_services",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if not self.is_temporary:
            return
        errors = {}
        if not self.temporary_type:
            errors["temporary_type"] = "Select Event or Temporary Service."
        if not self.barangay_id:
            errors["barangay"] = "Temporary offerings must belong to a barangay."
        if not self.start_datetime:
            errors["start_datetime"] = "Start date and time are required."
        if not self.end_datetime:
            errors["end_datetime"] = "End date and time are required."
        if self.start_datetime and self.end_datetime and self.end_datetime <= self.start_datetime:
            errors["end_datetime"] = "End date and time must be later than the start."
        if self.capacity is not None and self.capacity < 1:
            errors["capacity"] = "Capacity must be at least 1."
        if errors:
            raise ValidationError(errors)

    def computed_status(self, at=None, booking_count=None):
        if not self.is_temporary:
            return "active" if self.is_active else "deactivated"
        now = at or timezone.now()
        if self.lifecycle == self.Lifecycle.CANCELLED:
            return "cancelled"
        if not self.is_active:
            return "deactivated"
        if not self.start_datetime or not self.end_datetime:
            return "deactivated"
        if now >= self.end_datetime:
            return "expired"
        if self.capacity and booking_count is not None and booking_count >= self.capacity:
            return "fully_booked"
        if now < self.start_datetime:
            return "upcoming"
        duration = self.end_datetime - self.start_datetime
        threshold = min(timedelta(days=1), max(timedelta(hours=2), duration / 10))
        return "ending_soon" if now >= self.end_datetime - threshold else "active"

    def accepts_bookings(self, at=None, booking_count=None):
        return self.computed_status(at=at, booking_count=booking_count) in {"active", "ending_soon"}
