from django.db import migrations


SERVICES = (
    ("Barangay Clearance", "Request a barangay clearance.", 15),
    ("Certificate of Residency", "Request a certificate of residency.", 15),
    ("Business Permit Application", "Apply for a business permit.", 30),
    ("Certificate of Indigency", "Request a certificate of indigency.", 15),
    ("File Complaint", "Submit a barangay complaint.", 30),
)


def seed_services(apps, schema_editor):
    Service = apps.get_model("qq", "Service")
    for name, description, duration in SERVICES:
        Service.objects.update_or_create(
            name=name,
            defaults={
                "description": description,
                "estimated_duration": duration,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("qq", "0015_seed_signup_barangays")]

    operations = [migrations.RunPython(seed_services, migrations.RunPython.noop)]
