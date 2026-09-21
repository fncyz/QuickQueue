from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0024_barangaystaff_profile_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="admin_is_read",
            field=models.BooleanField(default=False),
        ),
    ]
