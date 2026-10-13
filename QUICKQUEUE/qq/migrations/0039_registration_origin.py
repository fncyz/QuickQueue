from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qq", "0038_barangayadministrator"),
    ]

    operations = [
        migrations.DeleteModel(
            name="BarangayAdministrator",
        ),
        migrations.AddField(
            model_name="barangayadminregistration",
            name="origin",
            field=models.CharField(
                choices=[
                    ("legacy_public", "Legacy public registration"),
                    ("superuser", "Created by superuser"),
                ],
                default="legacy_public",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="barangayadminregistration",
            name="terms_accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
