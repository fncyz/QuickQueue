from django.db import migrations, models


def add_service_codes(apps, schema_editor):
    Service = apps.get_model("qq", "Service")
    for service in Service.objects.all():
        words = [word for word in service.name.upper().split() if word]
        code = "".join(word[0] for word in words)[:5] or "SRV"
        service.code = code
        service.save(update_fields=["code"])


class Migration(migrations.Migration):
    dependencies = [("qq", "0016_seed_resident_booking_services")]

    operations = [
        migrations.AddField(
            model_name="service",
            name="code",
            field=models.CharField(blank=True, default="", help_text="Short service code used in queue numbers.", max_length=5),
        ),
        migrations.RunPython(add_service_codes, migrations.RunPython.noop),
    ]
