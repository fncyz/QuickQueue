from django.db import models

from .resident import Resident
from .appointment import Appointment


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        APPOINTMENT_CONFIRMED = "AC", "Appointment Confirmed"
        APPOINTMENT_REMINDER = "AR", "Appointment Reminder"
        QUEUE_UPDATE = "QU", "Queue Update"
        APPOINTMENT_CANCELLED = "CA", "Appointment Cancelled"
        APPOINTMENT_COMPLETED = "CO", "Appointment Completed"

    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

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
