from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_staff_from_barangay_users(apps, schema_editor):
    Barangay = apps.get_model("qq", "Barangay")
    BarangayStaff = apps.get_model("qq", "BarangayStaff")
    BarangayAdminRegistration = apps.get_model("qq", "BarangayAdminRegistration")

    for barangay in Barangay.objects.select_related("user").all():
        user = barangay.user
        if not user:
            continue
        if BarangayStaff.objects.filter(barangay=barangay, user=user).exists():
            continue

        registration = (
            BarangayAdminRegistration.objects.filter(barangay=barangay, user=user)
            .order_by("-created_at")
            .first()
        )
        first_name = user.first_name or user.username
        last_name = user.last_name or "Admin"
        BarangayStaff.objects.create(
            barangay=barangay,
            user=user,
            first_name=first_name,
            last_name=last_name,
            username=user.username,
            email=user.email or (registration.email if registration else ""),
            contact_number=registration.contact_number if registration else "",
            role="admin",
            is_active=user.is_active,
        )


def unseed_staff(apps, schema_editor):
    BarangayStaff = apps.get_model("qq", "BarangayStaff")
    BarangayStaff.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("qq", "0022_queueticket_claim_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="BarangayStaff",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_name", models.CharField(max_length=80)),
                ("last_name", models.CharField(max_length=80)),
                ("middle_name", models.CharField(blank=True, max_length=80)),
                ("username", models.CharField(max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("contact_number", models.CharField(blank=True, max_length=20)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("admin", "Barangay Admin"),
                            ("staff", "Barangay Staff"),
                            ("secretary", "Secretary"),
                            ("clerk", "Clerk"),
                        ],
                        default="staff",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "barangay",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_members",
                        to="qq.barangay",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="staff_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "barangay staff",
                "ordering": ("last_name", "first_name"),
            },
        ),
        migrations.RunPython(seed_staff_from_barangay_users, unseed_staff),
    ]
