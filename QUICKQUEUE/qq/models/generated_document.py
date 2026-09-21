from django.conf import settings
from django.db import models

from .document_template import DocumentTemplate
from .queue_tix import QueueTicket


def generated_upload_path(instance, filename):
    return f"generated_documents/barangay_{instance.template.barangay_id}/{filename}"


class GeneratedDocument(models.Model):
    class Status(models.TextChoices):
        GENERATED = "G", "Generated"
        ARCHIVED = "A", "Archived"

    ticket = models.OneToOneField(QueueTicket, on_delete=models.CASCADE, related_name="generated_document")
    template = models.ForeignKey(DocumentTemplate, on_delete=models.PROTECT, related_name="generated_documents")
    document_file = models.FileField(upload_to=generated_upload_path)
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.GENERATED)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    generated_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Document for {self.ticket}"
