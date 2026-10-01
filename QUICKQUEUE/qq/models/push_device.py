from django.db import models

from .resident import Resident


class PushDevice(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name="push_devices")
    expo_push_token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, blank=True)
    device_name = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.resident_id}: {self.device_name or self.platform or 'device'}"


class PushDelivery(models.Model):
    notification = models.ForeignKey("Notification", on_delete=models.CASCADE, related_name="push_deliveries")
    device = models.ForeignKey(PushDevice, on_delete=models.CASCADE, related_name="deliveries")
    expo_ticket_id = models.CharField(max_length=100, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["notification", "device"], name="unique_push_per_notification_device")
        ]
