from django.contrib.auth.models import User
from django.db import models

from .barangay import Barangay


class BarangayAdminRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="barangay_admin_registration")
    barangay = models.ForeignKey(Barangay, on_delete=models.PROTECT, related_name="admin_registrations")
    municipality = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    complete_address = models.TextField()
    zip_code = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField()
    terms_accepted_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.barangay} — {self.user.username}"
