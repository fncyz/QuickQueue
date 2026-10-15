from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("qq", "0040_role_based_notifications")]

    operations = [
        migrations.AddField(
            model_name="barangaystaff",
            name="must_change_password",
            field=models.BooleanField(default=False),
        ),
    ]
