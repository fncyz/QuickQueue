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

    service_window = models.ForeignKey(
        "ServiceWindow", on_delete=models.PROTECT, null=True, blank=True,
        related_name="queue_tickets",
    )

    served_by = models.ForeignKey(
        "BarangayStaff", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="served_queue_tickets",
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
    def activity_status(self):
        """Return the authoritative status used by current queue activity UIs."""
        if self.appointment.status == Appointment.Status.CANCELLED:
            return self.Status.CANCELLED
        if self.appointment.status == Appointment.Status.MISSED:
            return self.Status.MISSED
        if (
            self.claim_status == self.ClaimStatus.CLAIMED
            and self.appointment.status == Appointment.Status.COMPLETED
        ):
            return self.Status.COMPLETED
        return self.status

    @property
    def activity_status_display(self):
        if self.activity_status in (self.Status.CANCELLED, self.Status.MISSED):
            return dict(self.Status.choices)[self.activity_status]
        if self.activity_status == self.Status.COMPLETED:
            return "Completed"
        if self.claim_status == self.ClaimStatus.READY:
            return "Ready for Pickup"
        if self.claim_status == self.ClaimStatus.PROCESSING:
            return "Processing"
        return dict(self.Status.choices).get(self.activity_status, self.activity_status)

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
