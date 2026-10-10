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
        ARCHIVED = "archived", "Archived"
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
    event_start_date = models.DateField(null=True, blank=True)
    event_end_date = models.DateField(null=True, blank=True)
    booking_start_date = models.DateField(null=True, blank=True)
    booking_end_date = models.DateField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    lifecycle = models.CharField(max_length=12, choices=Lifecycle.choices, default=Lifecycle.SCHEDULED)
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
        if not self.event_start_date:
            errors["event_start_date"] = "Event start date is required."
        if not self.event_end_date:
            errors["event_end_date"] = "Event end date is required."
        if self.event_start_date and self.event_end_date and self.event_end_date < self.event_start_date:
            errors["event_end_date"] = "Event end date cannot be before the start date."
        if not self.booking_start_date:
            errors["booking_start_date"] = "Booking start date is required."
        if not self.booking_end_date:
            errors["booking_end_date"] = "Booking end date is required."
        if self.booking_start_date and self.booking_end_date and self.booking_end_date < self.booking_start_date:
            errors["booking_end_date"] = "Booking end date cannot be before the start date."
        if self.capacity is None or self.capacity < 1:
            errors["capacity"] = "Total slots must be at least 1."
        if errors:
            raise ValidationError(errors)

    def computed_status(self, at=None, booking_count=None):
        if not self.is_temporary:
            return "active" if self.is_active else "deactivated"
        current_date = timezone.localdate(at) if at else timezone.localdate()
        if self.lifecycle == self.Lifecycle.CANCELLED:
            return "cancelled"
        if self.lifecycle == self.Lifecycle.ARCHIVED:
            return "archived"
        if not self.is_active:
            return "deactivated"
        if not self.booking_start_date or not self.booking_end_date:
            return "deactivated"
        if self.event_end_date and current_date > self.event_end_date:
            return "expired"
        if current_date > self.booking_end_date:
            return "booking_closed"
        if self.capacity and booking_count is not None and booking_count >= self.capacity:
            return "fully_booked"
        if current_date < self.booking_start_date:
            return "upcoming"
        return "ending_soon" if current_date == self.booking_end_date else "active"

    def accepts_bookings(self, at=None, booking_count=None):
        current_date = timezone.localdate(at) if at else timezone.localdate()
        return bool(
            self.is_temporary
            and self.is_active
            and self.lifecycle == self.Lifecycle.SCHEDULED
            and self.booking_start_date
            and self.booking_end_date
            and self.event_end_date
            and self.booking_start_date <= current_date <= self.booking_end_date
            and current_date <= self.event_end_date
            and (not self.capacity or booking_count is None or booking_count < self.capacity)
        )
