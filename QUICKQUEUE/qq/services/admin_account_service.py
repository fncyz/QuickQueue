from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from qq.models import Barangay, BarangayAdminRegistration, BarangayStaff


def provision_admin_registration(registration, *, is_active=True):
    """Apply the established QuickQueue portal relationships for an approved registration."""
    user = registration.user
    user.is_active = is_active
    user.is_staff = False
    user.is_superuser = False
    user.email = registration.email
    user.save(update_fields=("is_active", "is_staff", "is_superuser", "email"))
    Barangay.objects.filter(user=user).exclude(pk=registration.barangay_id).update(user=None)
    barangay = registration.barangay
    barangay.user = user
    barangay.address = registration.complete_address
    barangay.contact_number = registration.contact_number
    barangay.email = registration.email
    barangay.save(update_fields=("user", "address", "contact_number", "email", "updated_at"))
    BarangayStaff.objects.update_or_create(
        user=user,
        defaults={
            "barangay": barangay,
            "first_name": user.first_name or user.username,
            "last_name": user.last_name or "Admin",
            "username": user.username,
            "email": registration.email,
            "contact_number": registration.contact_number,
            "role": BarangayStaff.Role.ADMIN,
            "is_active": is_active,
        },
    )


@transaction.atomic
def create_barangay_admin(cleaned_data):
    barangay = Barangay.objects.select_for_update().get(pk=cleaned_data["barangay"].pk)
    if barangay.user_id or BarangayStaff.objects.filter(barangay=barangay, role=BarangayStaff.Role.ADMIN).exists():
        raise ValueError("This barangay already has an administrator account.")
    user = User(
        username=cleaned_data["username"],
        first_name=cleaned_data["first_name"].strip(),
        last_name=cleaned_data["last_name"].strip(),
        email=cleaned_data["email"],
        is_active=cleaned_data.get("is_active", False),
        is_staff=False,
        is_superuser=False,
    )
    user.set_password(cleaned_data["password1"])
    user.save()
    registration = BarangayAdminRegistration.objects.create(
        user=user,
        barangay=barangay,
        municipality="Toledo City",
        province="Cebu",
        complete_address=barangay.address,
        zip_code="",
        contact_number=barangay.contact_number,
        email=user.email,
        origin=BarangayAdminRegistration.Origin.SUPERUSER,
        status=BarangayAdminRegistration.Status.APPROVED,
        reviewed_at=timezone.now(),
    )
    BarangayStaff.objects.create(
        user=user, barangay=barangay,
        first_name=user.first_name, last_name=user.last_name,
        username=user.username, email=user.email,
        contact_number=barangay.contact_number,
        role=BarangayStaff.Role.ADMIN, is_active=user.is_active,
        must_change_password=True,
    )
    barangay.user = user
    barangay.save(update_fields=("user", "updated_at"))
    return user, registration


@transaction.atomic
def update_barangay_admin(user, cleaned_data):
    old_barangay = getattr(user, "barangay_profile", None)
    profile = getattr(user, "staff_profile", None)
    if old_barangay is None and profile:
        old_barangay = profile.barangay
    new_barangay = Barangay.objects.select_for_update().get(pk=cleaned_data["barangay"].pk)
    conflict = new_barangay.user_id not in (None, user.pk)
    conflict = conflict or BarangayStaff.objects.filter(
        barangay=new_barangay, role=BarangayStaff.Role.ADMIN
    ).exclude(user=user).exists()
    if conflict:
        raise ValueError("This barangay already has an administrator account.")
    if old_barangay and old_barangay.pk != new_barangay.pk:
        old_barangay.user = None
        old_barangay.save(update_fields=("user", "updated_at"))
    new_barangay.user = user
    new_barangay.save(update_fields=("user", "updated_at"))
    user.first_name = cleaned_data["first_name"].strip()
    user.last_name = cleaned_data["last_name"].strip()
    user.email = cleaned_data["email"]
    user.is_active = cleaned_data.get("is_active", False)
    user.save(update_fields=("first_name", "last_name", "email", "is_active"))
    if profile is None:
        profile = BarangayStaff(
            user=user,
            username=user.username,
            contact_number=new_barangay.contact_number,
            role=BarangayStaff.Role.ADMIN,
        )
    profile.barangay = new_barangay
    profile.first_name = user.first_name
    profile.last_name = user.last_name
    profile.email = user.email
    profile.is_active = user.is_active
    profile.save()
    BarangayAdminRegistration.objects.filter(user=user).update(barangay=new_barangay, email=user.email)
    return user


@transaction.atomic
def approve_admin_registration(registration_id):
    registration = BarangayAdminRegistration.objects.select_for_update().select_related(
        "user", "barangay"
    ).get(pk=registration_id)
    if registration.status != BarangayAdminRegistration.Status.PENDING:
        raise ValueError("This application has already been processed.")
    barangay = Barangay.objects.select_for_update().get(pk=registration.barangay_id)
    user = registration.user
    conflicting_profile = BarangayStaff.objects.filter(
        barangay=barangay, role=BarangayStaff.Role.ADMIN
    ).exclude(user=user).exists()
    if barangay.user_id not in (None, user.pk) or conflicting_profile:
        raise ValueError("This barangay already has an administrator account.")
    if user.is_superuser or hasattr(user, "resident_profile"):
        raise ValueError("This account conflicts with another QuickQueue role.")

    provision_admin_registration(registration)
    registration.status = BarangayAdminRegistration.Status.APPROVED
    registration.reviewed_at = timezone.now()
    registration.save(update_fields=("status", "reviewed_at"))
    return registration


@transaction.atomic
def reject_admin_registration(registration_id):
    registration = BarangayAdminRegistration.objects.select_for_update().select_related("user").get(
        pk=registration_id
    )
    if registration.status != BarangayAdminRegistration.Status.PENDING:
        raise ValueError("This application has already been processed.")
    registration.status = BarangayAdminRegistration.Status.REJECTED
    registration.reviewed_at = timezone.now()
    registration.save(update_fields=("status", "reviewed_at"))
    registration.user.is_active = False
    registration.user.save(update_fields=("is_active",))
    return registration


@transaction.atomic
def reset_admin_password(user, temporary_password):
    profile = BarangayStaff.objects.select_for_update().get(
        user=user, role=BarangayStaff.Role.ADMIN
    )
    user.set_password(temporary_password)
    user.save(update_fields=("password",))
    profile.must_change_password = True
    profile.save(update_fields=("must_change_password", "updated_at"))
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        try:
            if str(session.get_decoded().get("_auth_user_id")) == str(user.pk):
                session.delete()
        except Exception:
            continue
    return profile
