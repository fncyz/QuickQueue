from django.db import models
from django.conf import settings

from .resident import Resident
from .appointment import Appointment
from .barangay import Barangay


class Notification(models.Model):

    class RecipientRole(models.TextChoices):
        RESIDENT = "resident", "Resident"
        STAFF = "staff", "Barangay staff"
        ADMIN = "admin", "Barangay admin"

    class NotificationType(models.TextChoices):
        APPOINTMENT_CONFIRMED = "AC", "Appointment Confirmed"
        APPOINTMENT_REMINDER = "AR", "Appointment Reminder"
        QUEUE_UPDATE = "QU", "Queue Update"
        APPOINTMENT_CANCELLED = "CA", "Appointment Cancelled"
        APPOINTMENT_COMPLETED = "CO", "Appointment Completed"
        STAFF_ALERT = "ST", "Staff Alert"
        DOCUMENT_UPDATE = "DU", "Document Update"
        EVENT_UPDATE = "EV", "Event Update"
        ADMIN_ALERT = "AD", "Administrative Alert"

    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quickqueue_notifications",
        null=True,
        blank=True,
    )

    recipient_role = models.CharField(
        max_length=10,
        choices=RecipientRole.choices,
        default=RecipientRole.RESIDENT,
    )

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    event_key = models.CharField(max_length=180, unique=True, null=True, blank=True)

    notification_type = models.CharField(
        max_length=2,
        choices=NotificationType.choices
    )

    title = models.CharField(
        max_length=100
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    admin_is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.resident_id:
            if not self.recipient_id:
                self.recipient_id = self.resident.user_id
            if not self.barangay_id:
                self.barangay_id = self.resident.barangay_id
        elif self.appointment_id and not self.barangay_id:
            self.barangay_id = self.appointment.barangay_id
        super().save(*args, **kwargs)
