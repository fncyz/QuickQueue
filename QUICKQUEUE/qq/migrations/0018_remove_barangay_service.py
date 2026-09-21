from django.db import migrations, models
import django.db.models.deletion


def copy_barangay_service_data(apps, schema_editor):
    Appointment = apps.get_model("qq", "Appointment")
    BarangayService = apps.get_model("qq", "BarangayService")

    for appointment in Appointment.objects.all():
        barangay_service = BarangayService.objects.get(pk=appointment.barangay_service_id)
        appointment.barangay_id = barangay_service.barangay_id
        appointment.service_id = barangay_service.service_id
        appointment.save(update_fields=["barangay_id", "service_id"])


class Migration(migrations.Migration):
    dependencies = [("qq", "0017_service_code")]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="barangay",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointments",
                to="qq.barangay",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="service",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointments",
                to="qq.service",
            ),
        ),
        migrations.RunPython(copy_barangay_service_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="queue_number",
            field=models.CharField(max_length=10),
        ),
        migrations.RemoveField(
            model_name="appointment",
            name="barangay_service",
        ),
        migrations.AlterField(
            model_name="appointment",
            name="barangay",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointments",
                to="qq.barangay",
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="service",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointments",
                to="qq.service",
            ),
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.UniqueConstraint(
                fields=("appointment_date", "barangay", "service", "queue_number"),
                name="unique_queue_per_day",
            ),
        ),
        migrations.DeleteModel(
            name="BarangayService",
        ),
    ]
