import uuid

from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resident = models.ForeignKey("Resident", on_delete=models.CASCADE, related_name="chat_sessions")
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        RESIDENT = "resident", "Resident"
        ASSISTANT = "assistant", "Assistant"

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    text = models.TextField()
    source = models.CharField(max_length=40, blank=True)
    error_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")


class ChatFeedback(models.Model):
    message = models.OneToOneField(ChatMessage, on_delete=models.CASCADE, related_name="feedback")
    resident = models.ForeignKey("Resident", on_delete=models.CASCADE, related_name="chat_feedback")
    helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatQuestionTopic(models.Model):
    normalized_question = models.CharField(max_length=500, unique=True)
    example_question = models.CharField(max_length=500)
    count = models.PositiveIntegerField(default=1)
    unanswered_count = models.PositiveIntegerField(default=0)
    last_asked_at = models.DateTimeField(auto_now=True)


class AssistantKnowledge(models.Model):
    barangay = models.ForeignKey(
        "Barangay", on_delete=models.CASCADE, related_name="assistant_knowledge",
        null=True, blank=True,
    )
    title = models.CharField(max_length=160)
    content = models.TextField()
    keywords = models.CharField(max_length=500, blank=True)
    is_approved = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_assistant_knowledge",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title",)
