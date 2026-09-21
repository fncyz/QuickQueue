from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from pathlib import Path

from qq.models import Barangay, BarangayStaff, Notification


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        return user.staff_profile.barangay
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


def _staff_for(user):
    try:
        return user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("No staff profile is linked to this account.") from error


@login_required(login_url="signin")
def barangay_settings(request):
    """Display and update the signed-in barangay staff member's account settings."""
    if (
        hasattr(request.user, "staff_profile")
        and not hasattr(request.user, "barangay_profile")
        and request.user.staff_profile.role != BarangayStaff.Role.ADMIN
    ):
        return redirect("staff_settings")
    barangay = _barangay_for(request.user)
    staff = _staff_for(request.user)
    today = timezone.localdate()
    active_tab = request.GET.get("tab", "profile")
    if active_tab not in ("profile", "password"):
        active_tab = "profile"

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            _update_profile(request, staff)
            active_tab = "profile"
        elif action == "password":
            _update_password(request)
            active_tab = "password"
        return redirect(f"{reverse('barangay_settings')}?tab={active_tab}")

    last_login = request.user.last_login
    return render(
        request,
        "barangay_admin/settings.html",
        {
            "barangay": barangay,
            "staff": staff,
            "today": today,
            "active_page": "settings",
            "active_tab": active_tab,
            "last_login": last_login,
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )


def _update_profile(request, staff):
    user = request.user
    fields = ("first_name", "last_name", "middle_name", "email", "contact_number")
    values = {field: request.POST.get(field, "").strip() for field in fields}
    photo = request.FILES.get("profile_photo")
    if not values["first_name"] or not values["last_name"]:
        messages.error(request, "First name and last name are required.")
        return
    if photo:
        allowed_types = {"image/jpeg", "image/png"}
        if photo.content_type not in allowed_types or Path(photo.name).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            messages.error(request, "Profile photo must be a JPG or PNG image.")
            return
        if photo.size > 5 * 1024 * 1024:
            messages.error(request, "Profile photo must not exceed 5MB.")
            return
    try:
        with transaction.atomic():
            for field, value in values.items():
                setattr(staff, field, value)
            if photo:
                staff.profile_photo = photo
            staff.save()
            user.first_name = values["first_name"]
            user.last_name = values["last_name"]
            user.email = values["email"]
            user.save(update_fields=("first_name", "last_name", "email"))
        messages.success(request, "Your profile has been updated.")
    except IntegrityError:
        messages.error(request, "That email address is already in use.")


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
