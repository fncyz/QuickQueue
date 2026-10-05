import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("qq", "0031_service_temporary_events"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="EventBooking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("booking_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("confirmed", "Confirmed"), ("checked_in", "Checked In"), ("cancelled", "Cancelled")], default="confirmed", max_length=12)),
                ("checked_in_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("appointment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="event_booking", to="qq.appointment")),
                ("checked_in_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="event_checkins", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
