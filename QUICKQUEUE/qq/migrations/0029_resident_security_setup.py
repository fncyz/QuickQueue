from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("qq", "0028_documenttemplate_generateddocument_and_more")]

    operations = [
        migrations.AddField(
            model_name="resident",
            name="pin_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="resident",
            name="security_setup_stage",
            field=models.CharField(
                choices=[
                    ("password", "Create Password"),
                    ("pin", "Set Secure PIN"),
                    ("fingerprint", "Fingerprint"),
                    ("face", "Face Recognition"),
                    ("complete", "Complete"),
                ],
                default="complete",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="resident",
            name="security_setup_stage",
            field=models.CharField(
                choices=[
                    ("password", "Create Password"),
                    ("pin", "Set Secure PIN"),
                    ("fingerprint", "Fingerprint"),
                    ("face", "Face Recognition"),
                    ("complete", "Complete"),
                ],
                default="password",
                max_length=20,
            ),
        ),
    ]
