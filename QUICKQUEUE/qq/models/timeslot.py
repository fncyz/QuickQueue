from django.db import models
from .barangay import Barangay
from django.core.exceptions import ValidationError

def clean(self):
    if self.end_time <= self.start_time:
        raise ValidationError(
            "End time must be later than the start time."
        )


class TimeSlot(models.Model):

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        related_name="time_slots",
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    max_appointments = models.PositiveIntegerField(
        default=5
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["start_time"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "barangay",
                    "start_time",
                    "end_time",
                ],
                name="unique_barangay_timeslot",
            )
        ]

    def __str__(self):
        return (
            f"{self.barangay.name} "
            f"({self.start_time} - {self.end_time})"
        )