from django.conf import settings
from django.core.mail import send_mail


def send_account_credentials(
    *,
    email,
    username,
    password,
):
    """
    Sends the resident's account credentials
    to their email address.
    """

    subject = "Welcome to QuickQueue"

    message = f"""
Hello!

Your QuickQueue account has been created successfully.

Your login credentials are:

Username: {username}

Temporary Password: {password}

For your security, please change your password after your first login.

Thank you for using QuickQueue!
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )