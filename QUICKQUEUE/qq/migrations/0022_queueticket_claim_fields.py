from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0021_barangayadminregistration"),
    ]

    operations = [
        migrations.AddField(
            model_name="queueticket",
            name="claim_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Not applicable"),
                    ("P", "Processing"),
                    ("R", "Ready for Claiming"),
                    ("L", "Claimed"),
                ],
                default="",
                help_text="Document claim workflow after service completion.",
                max_length=1,
            ),
        ),
        migrations.AddField(
            model_name="queueticket",
            name="requirements",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Additional requirements shown while documents are processing.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="queueticket",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="queueticket",
            name="claimed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
