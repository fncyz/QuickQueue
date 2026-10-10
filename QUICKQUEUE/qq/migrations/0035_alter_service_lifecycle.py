from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0034_booking_configuration"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="lifecycle",
            field=models.CharField(
                choices=[
                    ("scheduled", "Scheduled"),
                    ("cancelled", "Cancelled"),
                    ("archived", "Archived"),
                ],
                default="scheduled",
                max_length=12,
            ),
        ),
    ]
