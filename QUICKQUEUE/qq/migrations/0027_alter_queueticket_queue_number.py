from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0026_appointment_sitio"),
    ]

    operations = [
        migrations.AlterField(
            model_name="queueticket",
            name="queue_number",
            field=models.CharField(max_length=10),
        ),
    ]
