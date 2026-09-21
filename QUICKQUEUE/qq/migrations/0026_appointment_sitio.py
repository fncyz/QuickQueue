from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0025_notification_admin_is_read"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="sitio",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
