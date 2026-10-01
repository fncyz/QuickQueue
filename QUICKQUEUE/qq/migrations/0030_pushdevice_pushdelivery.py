from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("qq", "0029_resident_security_setup")]
    operations = [
        migrations.CreateModel(
            name="PushDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expo_push_token", models.CharField(max_length=255, unique=True)),
                ("platform", models.CharField(blank=True, max_length=20)),
                ("device_name", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="push_devices", to="qq.resident")),
            ],
        ),
        migrations.CreateModel(
            name="PushDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expo_ticket_id", models.CharField(blank=True, max_length=100)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="qq.pushdevice")),
                ("notification", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="push_deliveries", to="qq.notification")),
            ],
        ),
        migrations.AddConstraint(model_name="pushdelivery", constraint=models.UniqueConstraint(fields=("notification", "device"), name="unique_push_per_notification_device")),
    ]
