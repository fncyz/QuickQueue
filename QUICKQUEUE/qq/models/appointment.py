from django.db import models

from .barangay import Barangay
from .resident import Resident
from .services import Service
from .timeslot import TimeSlot


class Appointment(models.Model):

    class Status(models.TextChoices):
        PENDING = "P", "Pending"
        CONFIRMED = "C", "Confirmed"
        ONGOING = "O", "Ongoing"
        COMPLETED = "D", "Completed"
        CANCELLED = "X", "Cancelled"
        MISSED = "M", "Missed"

    resident = models.ForeignKey(
        Resident,
        on_delete=models.PROTECT,
        related_name="appointments"
    )

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    purpose = models.TextField(
        blank=True
    )

    sitio = models.CharField(
        max_length=100,
        blank=True,
    )

    appointment_date = models.DateField()

    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    queue_number = models.CharField(
        max_length=10,
    )

    status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "appointment_date",
            "time_slot",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "appointment_date",
                    "barangay",
                    "service",
                    "queue_number",
                ],
                name="unique_queue_per_day",
            )
        ]

    def __str__(self):
        return (
            f"{self.queue_number} | "
            f"{self.resident.first_name} {self.resident.last_name}"
        )
