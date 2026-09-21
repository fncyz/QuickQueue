from django.db import models

from .appointment import Appointment


class QueueTicket(models.Model):

    class Status(models.TextChoices):
        WAITING = "W", "Waiting"
        NOW_SERVING = "S", "Now Serving"
        COMPLETED = "C", "Completed"
        MISSED = "M", "Missed"
        CANCELLED = "X", "Cancelled"

    class ClaimStatus(models.TextChoices):
        NONE = "", "Not applicable"
        PROCESSING = "P", "Processing"
        READY = "R", "Ready for Claiming"
        CLAIMED = "L", "Claimed"

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="queue_ticket",
    )

    queue_number = models.CharField(
        max_length=10,
    )

    status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.WAITING,
    )

    claim_status = models.CharField(
        max_length=1,
        choices=ClaimStatus.choices,
        blank=True,
        default=ClaimStatus.NONE,
        help_text="Document claim workflow after service completion.",
    )

    requirements = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Additional requirements shown while documents are processing.",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    called_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    claimed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.queue_number

    @property
    def processing_duration_label(self):
        if not self.called_at or not self.completed_at:
            return "—"
        seconds = (self.completed_at - self.called_at).total_seconds()
        if seconds < 0:
            return "—"
        minutes = int(seconds // 60)
        rem = int(seconds % 60)
        if minutes <= 0:
            return f"{rem}s"
        return f"{minutes}m {rem:02d}s"
