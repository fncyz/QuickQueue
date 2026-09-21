from django.db import migrations


BARANGAYS = (
    "Poblacion",
    "Luray 2",
    "Bato",
    "Sangi",
    "Daanlungsod",
)


def add_signup_barangays(apps, schema_editor):
    Barangay = apps.get_model("qq", "Barangay")
    for name in BARANGAYS:
        Barangay.objects.update_or_create(
            name=name,
            defaults={
                "address": "Toledo City, Cebu",
                "contact_number": "",
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0014_alter_resident_municipality_alter_resident_province"),
    ]

    operations = [
        migrations.RunPython(add_signup_barangays, migrations.RunPython.noop),
    ]
