from datetime import date

from django.contrib.auth.models import User
from django.db import models

from .barangay import Barangay


class Resident(models.Model):

    class Sex(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="resident_profile"
    )

    first_name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=100
    )

    middle_name = models.CharField(
        max_length=100,
        blank=True
    )

    suffix = models.CharField(
        max_length=20,
        blank=True
    )

    birthdate = models.DateField()

    sex = models.CharField(
        max_length=1,
        choices=Sex.choices
    )

    email = models.EmailField(
        unique=True,
        blank=True,
        null=True,
    )

    contact_number = models.CharField(
        max_length=15,
        unique=True
    )

    province = models.CharField(
        max_length=100,
        default="Cebu"
    )

    municipality = models.CharField(
        max_length=100,
        default="Toledo City"
    )

    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.PROTECT,
        related_name="residents"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """Return the resident's current age derived from their birthdate."""
        today = date.today()
        return today.year - self.birthdate.year - (
            (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
        )
