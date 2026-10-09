import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0033_remove_appointment_unique_queue_per_day_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="service_fee_snapshot",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="Service fee at the time the appointment was booked.", max_digits=10, null=True),
        ),
        migrations.CreateModel(
            name="BarangayBookingConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("daily_capacity", models.PositiveIntegerField(default=30)),
                ("office_start_time", models.TimeField(default=datetime.time(8, 0))),
                ("office_end_time", models.TimeField(default=datetime.time(16, 0))),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("barangay", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="booking_configuration", to="qq.barangay")),
            ],
        ),
        migrations.CreateModel(
            name="BarangayServiceConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("estimated_duration", models.PositiveIntegerField(default=15)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("barangay", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_configurations", to="qq.barangay")),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="barangay_configurations", to="qq.service")),
            ],
            options={"ordering": ("service__name",)},
        ),
        migrations.CreateModel(
            name="ClosedAppointmentDate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("reason", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("barangay", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="closed_appointment_dates", to="qq.barangay")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="closed_appointment_dates", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("date",)},
        ),
        migrations.AddConstraint(
            model_name="barangayserviceconfiguration",
            constraint=models.UniqueConstraint(fields=("barangay", "service"), name="unique_barangay_service_configuration"),
        ),
        migrations.AddConstraint(
            model_name="closedappointmentdate",
            constraint=models.UniqueConstraint(fields=("barangay", "date"), name="unique_closed_date_per_barangay"),
        ),
    ]
