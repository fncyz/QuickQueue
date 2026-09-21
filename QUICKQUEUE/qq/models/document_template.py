from django.conf import settings
from django.db import models

from .barangay import Barangay
from .services import Service


def template_upload_path(instance, filename):
    return f"document_templates/barangay_{instance.barangay_id}/service_{instance.service_id}/{filename}"


class DocumentTemplate(models.Model):
    """A barangay-owned source template used for a particular service."""

    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name="document_templates")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="document_templates")
    name = models.CharField(max_length=150)
    template_file = models.FileField(upload_to=template_upload_path)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("barangay", "service"), name="unique_template_per_barangay_service")]
        ordering = ("service__name",)

    def __str__(self):
        return f"{self.barangay} · {self.service} v{self.version}"
