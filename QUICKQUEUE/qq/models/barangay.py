from django.db import models
from django.contrib.auth.models import User


class Barangay(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="barangay_profile",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100,
        unique=True
    )

    address = models.TextField()

    contact_number = models.CharField(
        max_length=15
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    daily_booking_capacity = models.PositiveIntegerField(
        default=30,
        editable=False,
        help_text="Maximum number of regular appointments residents may book per day.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name
