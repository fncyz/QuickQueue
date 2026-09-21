from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render


@login_required(login_url="signin")
def resident_profile(request):
    """Display and safely update the signed-in resident's profile."""
    resident = request.user.resident_profile
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            _update_profile(request, resident)
        elif action == "password":
            _update_password(request)
        return redirect("resident_profile")

    return render(
        request,
        "resident/profile.html",
        {"resident": resident, "active_page": "profile"},
    )


def _update_profile(request, resident):
    fields = ("first_name", "last_name", "middle_name", "email", "contact_number")
    values = {field: request.POST.get(field, "").strip() for field in fields}
    if not values["first_name"] or not values["last_name"] or not values["contact_number"]:
        messages.error(request, "First name, last name, and contact number are required.")
        return
    if not values["contact_number"].isdigit():
        messages.error(request, "Contact number must contain digits only.")
        return
    try:
        with transaction.atomic():
            for field, value in values.items():
                setattr(resident, field, value or None if field == "email" else value)
            resident.save()
        messages.success(request, "Your profile has been updated.")
    except IntegrityError:
        messages.error(request, "That email address or contact number is already in use.")


def _update_password(request):
    user = request.user
    current = request.POST.get("current_password", "")
    new = request.POST.get("new_password", "")
    confirm = request.POST.get("confirm_password", "")
    if not user.check_password(current):
        messages.error(request, "Your current password is incorrect.")
        return
    if new != confirm:
        messages.error(request, "The new password and confirmation do not match.")
        return
    try:
        validate_password(new, user)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return
    user.set_password(new)
    user.save()
    update_session_auth_hash(request, user)
    messages.success(request, "Password updated successfully.")
