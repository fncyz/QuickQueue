from django.conf import settings
from django.db import models

from .barangay import Barangay
from .services import Service


class BarangayServiceConfiguration(models.Model):
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name="service_configurations")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="barangay_configurations")
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_duration = models.PositiveIntegerField(default=15)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("barangay", "service"), name="unique_barangay_service_configuration")
        ]
        ordering = ("service__name",)


class ClosedAppointmentDate(models.Model):
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name="closed_appointment_dates")
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_appointment_dates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("barangay", "date"), name="unique_closed_date_per_barangay")
        ]
        ordering = ("date",)
