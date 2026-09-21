from django.db import models


class Service(models.Model):
    code = models.CharField(
        max_length=5,
        blank=True,
        default="",
        help_text="Short service code used in queue numbers."
    )
    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField()

    requirements = models.TextField(
        blank=True,
        help_text="Requirements needed for this service."
    )

    estimated_duration = models.PositiveIntegerField(
        help_text="Estimated processing time in minutes."
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name
