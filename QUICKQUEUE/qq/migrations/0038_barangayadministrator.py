from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0037_servicewindow_queueticket_window"),
    ]

    operations = [
        migrations.CreateModel(
            name="BarangayAdministrator",
            fields=[],
            options={
                "verbose_name": "barangay admin",
                "verbose_name_plural": "barangay admins",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("qq.barangaystaff",),
        ),
    ]
