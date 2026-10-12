import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("qq", "0035_alter_service_lifecycle"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="ChatQuestionTopic", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("normalized_question", models.CharField(max_length=500, unique=True)),
            ("example_question", models.CharField(max_length=500)),
            ("count", models.PositiveIntegerField(default=1)),
            ("unanswered_count", models.PositiveIntegerField(default=0)),
            ("last_asked_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="ChatSession", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("summary", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("resident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_sessions", to="qq.resident")),
        ]),
        migrations.CreateModel(name="AssistantKnowledge", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=160)), ("content", models.TextField()),
            ("keywords", models.CharField(blank=True, max_length=500)), ("is_approved", models.BooleanField(default=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("barangay", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="assistant_knowledge", to="qq.barangay")),
            ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_assistant_knowledge", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ("title",)}),
        migrations.CreateModel(name="ChatMessage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("role", models.CharField(choices=[("resident", "Resident"), ("assistant", "Assistant")], max_length=10)),
            ("text", models.TextField()), ("source", models.CharField(blank=True, max_length=40)),
            ("error_code", models.CharField(blank=True, max_length=40)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="qq.chatsession")),
        ], options={"ordering": ("created_at", "pk")}),
        migrations.CreateModel(name="ChatFeedback", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("helpful", models.BooleanField()), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("message", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="feedback", to="qq.chatmessage")),
            ("resident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_feedback", to="qq.resident")),
        ]),
    ]
