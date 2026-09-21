from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0023_barangaystaff"),
    ]

    operations = [
        migrations.AddField(
            model_name="barangaystaff",
            name="profile_photo",
            field=models.FileField(blank=True, upload_to="staff/profile_photos/"),
        ),
    ]
