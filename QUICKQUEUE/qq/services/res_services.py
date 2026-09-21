import secrets

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from qq.models import Resident
from qq.services.email_service import send_account_credentials


def check_duplicate_email(email):
    """
    Returns True if the email is already registered.
    """
    return bool(email) and Resident.objects.filter(
        email=email
    ).exists()


def check_duplicate_contact_number(contact_number):
    """
    Returns True if the contact number is already registered.
    """
    return Resident.objects.filter(
        contact_number=contact_number
    ).exists()


def generate_temporary_password():
    """
    Generates a secure temporary password.
    """
    return secrets.token_urlsafe(8)


def check_duplicate_username(username):
    """Returns True if the username is already registered."""
    return User.objects.filter(username__iexact=username).exists()


@transaction.atomic
def create_resident(
    *,
    username,
    first_name,
    middle_name,
    last_name,
    suffix,
    birthdate,
    sex,
    email,
    contact_number,
    barangay,
    province,
    municipality,
    send_credentials=False,
):
    """
    Creates a Resident account together with its
    Django authentication User account and
    optionally emails the generated credentials.
    """

    if check_duplicate_email(email):
        raise ValueError(
            "Email address is already registered."
        )

    if not contact_number.isdigit():
        raise ValueError("Contact number must contain digits only.")

    if check_duplicate_contact_number(contact_number):
        raise ValueError(
            "Contact number is already registered."
        )

    if check_duplicate_username(username):
        raise ValueError("Username is already taken.")

    password = generate_temporary_password()

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )

    resident = Resident.objects.create(
        user=user,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        suffix=suffix,
        birthdate=birthdate,
        sex=sex,
        email=email,
        contact_number=contact_number,
        province=province,
        municipality=municipality,
        barangay=barangay,
        terms_accepted_at=timezone.now(),
    )

    if send_credentials:
        send_account_credentials(
            email=email,
            username=username,
            password=password,
        )

    return resident, username, password
