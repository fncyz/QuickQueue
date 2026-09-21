from django.contrib.auth.models import User
from django.db import models

from .barangay import Barangay


class BarangayStaff(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Barangay Admin"
        STAFF = "staff", "Barangay Staff"
        SECRETARY = "secretary", "Secretary"
        CLERK = "clerk", "Clerk"

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.CASCADE,
        related_name="staff_members",
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profile",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    username = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.FileField(upload_to="staff/profile_photos/", blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("last_name", "first_name")
        verbose_name_plural = "barangay staff"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.barangay.name})"

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)

    @property
    def initials(self):
        first = self.first_name[:1] if self.first_name else ""
        last = self.last_name[:1] if self.last_name else ""
        return f"{first}{last}".upper() or "?"
