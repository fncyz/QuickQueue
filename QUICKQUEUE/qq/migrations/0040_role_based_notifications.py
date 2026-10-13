from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_recipients(apps, schema_editor):
    Notification = apps.get_model("qq", "Notification")
    for notification in Notification.objects.select_related("resident", "appointment").iterator():
        notification.recipient_id = notification.resident.user_id if notification.resident_id else None
        notification.barangay_id = (
            notification.resident.barangay_id if notification.resident_id
            else notification.appointment.barangay_id if notification.appointment_id else None
        )
        notification.recipient_role = "resident"
        notification.save(update_fields=("recipient", "barangay", "recipient_role"))


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("qq", "0039_registration_origin"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification", name="appointment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="qq.appointment"),
        ),
        migrations.AlterField(
            model_name="notification", name="resident",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="qq.resident"),
        ),
        migrations.AddField(
            model_name="notification", name="barangay",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="qq.barangay"),
        ),
        migrations.AddField(
            model_name="notification", name="event_key",
            field=models.CharField(blank=True, max_length=180, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="notification", name="recipient",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="quickqueue_notifications", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="notification", name="recipient_role",
            field=models.CharField(choices=[("resident", "Resident"), ("staff", "Barangay staff"), ("admin", "Barangay admin")], default="resident", max_length=10),
        ),
        migrations.AlterField(
            model_name="notification", name="notification_type",
            field=models.CharField(choices=[("AC", "Appointment Confirmed"), ("AR", "Appointment Reminder"), ("QU", "Queue Update"), ("CA", "Appointment Cancelled"), ("CO", "Appointment Completed"), ("ST", "Staff Alert"), ("DU", "Document Update"), ("EV", "Event Update"), ("AD", "Administrative Alert")], max_length=2),
        ),
        migrations.RunPython(backfill_recipients, migrations.RunPython.noop),
    ]
