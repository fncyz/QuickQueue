from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("qq", "0030_pushdevice_pushdelivery"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="service", name="is_temporary", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="service", name="temporary_type", field=models.CharField(blank=True, choices=[("event", "Event"), ("temporary_service", "Temporary Service")], max_length=20)),
        migrations.AddField(model_name="service", name="barangay", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="temporary_services", to="qq.barangay")),
        migrations.AddField(model_name="service", name="location", field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name="service", name="start_datetime", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="service", name="end_datetime", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="service", name="slot_duration", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="service", name="capacity", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="service", name="lifecycle", field=models.CharField(choices=[("scheduled", "Scheduled"), ("cancelled", "Cancelled")], default="scheduled", max_length=12)),
        migrations.AddField(model_name="service", name="available_time_slots", field=models.ManyToManyField(blank=True, related_name="temporary_services", to="qq.timeslot")),
        migrations.AddField(model_name="service", name="created_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_temporary_services", to=settings.AUTH_USER_MODEL)),
    ]
