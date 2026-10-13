from pathlib import Path

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

from qq.models import Barangay, BarangayStaff, Notification, QueueTicket, ServiceWindow


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
    """Admin account settings; operational settings live in the staff portal."""
    if (
        hasattr(request.user, "staff_profile")
        and not hasattr(request.user, "barangay_profile")
        and request.user.staff_profile.role != BarangayStaff.Role.ADMIN
    ):
        return redirect("staff_settings")
    barangay = _barangay_for(request.user)
    staff = _staff_for(request.user)
    active_tab = request.GET.get("tab", "profile")
    if active_tab not in ("profile", "password", "windows"):
        active_tab = "profile"
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "window_count":
            _configure_windows(request, barangay)
            active_tab = "windows"
        elif action == "window_update":
            _update_window(request, barangay)
            active_tab = "windows"
        elif action == "password":
            _update_password(request)
            active_tab = "password"
        else:
            _update_profile(request, staff)
            active_tab = "profile"
        return redirect(f"{reverse('barangay_settings')}?tab={active_tab}")
    windows = list(ServiceWindow.objects.filter(barangay=barangay).select_related("assigned_staff"))
    return render(request, "barangay_admin/settings.html", {
        "barangay": barangay,
        "staff": staff,
        "today": timezone.localdate(),
        "active_page": "settings",
        "active_tab": active_tab,
        "last_login": request.user.last_login,
        "windows": windows,
        "eligible_staff": BarangayStaff.objects.filter(barangay=barangay, is_active=True).exclude(role=BarangayStaff.Role.ADMIN),
        "window_stats": {
            "available": sum(window.is_active for window in windows),
            "assigned": sum(bool(window.is_active and window.assigned_staff_id) for window in windows),
            "unassigned": sum(bool(window.is_active and not window.assigned_staff_id) for window in windows),
        },
        "unread_notifications": Notification.objects.filter(
            appointment__barangay=barangay, admin_is_read=False
        ).count(),
    })


def _configure_windows(request, barangay):
    try:
        requested = int(request.POST.get("total_windows", ""))
    except ValueError:
        requested = 0
    if requested < 1 or requested > 50:
        messages.error(request, "Total windows must be a positive number no greater than 50.")
        return
    with transaction.atomic():
        existing = list(ServiceWindow.objects.select_for_update().filter(barangay=barangay))
        by_number = {window.number: window for window in existing}
        for number in range(1, requested + 1):
            if number not in by_number:
                ServiceWindow.objects.create(barangay=barangay, number=number, name=f"Window {number}")
        affected = []
        for window in existing:
            if window.number <= requested:
                continue
            if window.assigned_staff_id or window.queue_tickets.exists():
                if window.is_active:
                    window.is_active = False
                    window.save(update_fields=("is_active", "updated_at"))
                affected.append(window.name)
            else:
                window.delete()
    if affected:
        messages.warning(request, f"Saved {requested} active windows. Historical or assigned windows were deactivated: {', '.join(affected)}.")
    else:
        messages.success(request, f"Window configuration saved with {requested} windows.")


def _update_window(request, barangay):
    try:
        window_id = int(request.POST.get("window_id", ""))
    except ValueError:
        messages.error(request, "Invalid service window.")
        return
    with transaction.atomic():
        try:
            window = ServiceWindow.objects.select_for_update().get(pk=window_id, barangay=barangay)
        except ServiceWindow.DoesNotExist:
            messages.error(request, "Service window not found.")
            return
        action = request.POST.get("window_action", "save")
        if action == "delete":
            if window.assigned_staff_id or window.queue_tickets.exists():
                messages.error(request, "Assigned windows and windows with queue history cannot be removed. Deactivate this window instead.")
                return
            window.delete()
            messages.success(request, "Unused service window removed.")
            return
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Window name is required.")
            return
        staff_id = request.POST.get("assigned_staff", "").strip()
        assigned_staff = None
        if staff_id:
            assigned_staff = BarangayStaff.objects.filter(pk=staff_id, barangay=barangay, is_active=True).exclude(role=BarangayStaff.Role.ADMIN).first()
            if not assigned_staff:
                messages.error(request, "Select an eligible staff member from this barangay.")
                return
            ServiceWindow.objects.select_for_update().filter(
                barangay=barangay, assigned_staff=assigned_staff, is_active=True,
            ).exclude(pk=window.pk).update(assigned_staff=None)
        window.name = name[:80]
        window.assigned_staff = assigned_staff
        window.is_active = request.POST.get("is_active") == "on"
        window.save(update_fields=("name", "assigned_staff", "is_active", "updated_at"))
    messages.success(request, f"{window.name} updated successfully.")


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
