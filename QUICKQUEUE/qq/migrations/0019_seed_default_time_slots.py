from datetime import time

from django.db import migrations


DEFAULT_TIME_SLOTS = (
    (time(8, 0), time(9, 0)),
    (time(9, 0), time(10, 0)),
    (time(10, 0), time(11, 0)),
    (time(13, 0), time(14, 0)),
    (time(14, 0), time(15, 0)),
    (time(15, 0), time(16, 0)),
)


def seed_default_time_slots(apps, schema_editor):
    Barangay = apps.get_model("qq", "Barangay")
    TimeSlot = apps.get_model("qq", "TimeSlot")

    for barangay in Barangay.objects.all():
        for start_time, end_time in DEFAULT_TIME_SLOTS:
            TimeSlot.objects.get_or_create(
                barangay=barangay,
                start_time=start_time,
                end_time=end_time,
                defaults={
                    "is_active": True,
                    "max_appointments": 5,
                },
            )


class Migration(migrations.Migration):
    dependencies = [("qq", "0018_remove_barangay_service")]

    operations = [
        migrations.RunPython(seed_default_time_slots, migrations.RunPython.noop),
    ]
