from django.db import models
from django.db.models import Q

from .barangay import Barangay
from .barangay_staff import BarangayStaff


class ServiceWindow(models.Model):
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name="service_windows")
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    assigned_staff = models.ForeignKey(
        BarangayStaff, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="service_window_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("number",)
        constraints = [
            models.UniqueConstraint(fields=("barangay", "number"), name="unique_window_number_per_barangay"),
            models.UniqueConstraint(
                fields=("assigned_staff",), condition=Q(is_active=True, assigned_staff__isnull=False),
                name="unique_active_window_per_staff",
            ),
        ]

    @property
    def operational_status(self):
        if not self.is_active:
            return "inactive"
        if not self.assigned_staff_id:
            return "unassigned"
        if self.queue_tickets.filter(status="S").exists():
            return "busy"
        return "active"

    def __str__(self):
        return self.name
