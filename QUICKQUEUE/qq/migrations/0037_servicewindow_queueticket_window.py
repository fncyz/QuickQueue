import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("qq", "0036_ai_assistant_learning")]

    operations = [
        migrations.CreateModel(
            name="ServiceWindow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveIntegerField()),
                ("name", models.CharField(max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_staff", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_window_assignments", to="qq.barangaystaff")),
                ("barangay", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_windows", to="qq.barangay")),
            ],
            options={"ordering": ("number",)},
        ),
        migrations.AddConstraint(model_name="servicewindow", constraint=models.UniqueConstraint(fields=("barangay", "number"), name="unique_window_number_per_barangay")),
        migrations.AddConstraint(model_name="servicewindow", constraint=models.UniqueConstraint(condition=models.Q(("assigned_staff__isnull", False), ("is_active", True)), fields=("assigned_staff",), name="unique_active_window_per_staff")),
        migrations.AddField(model_name="queueticket", name="service_window", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="queue_tickets", to="qq.servicewindow")),
        migrations.AddField(model_name="queueticket", name="served_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="served_queue_tickets", to="qq.barangaystaff")),
    ]
