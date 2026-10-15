from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from qq.forms import SuperAdminProfileForm
from qq.models import Appointment, Barangay, BarangayStaff, Resident


def _require_superuser(request):
    if not request.user.is_superuser:
        raise PermissionDenied


def _settings_context(request, *, profile_form=None, password_form=None):
    direct_admin_ids = set(Barangay.objects.exclude(user_id=None).values_list("user_id", flat=True))
    staff_admin_ids = set(
        BarangayStaff.objects.filter(role=BarangayStaff.Role.ADMIN, user__isnull=False)
        .values_list("user_id", flat=True)
    )
    password_form = password_form or PasswordChangeForm(request.user)
    password_form.fields["old_password"].label = "Current Password"
    password_form.fields["new_password1"].label = "New Password"
    password_form.fields["new_password2"].label = "Confirm New Password"
    for field in password_form.fields.values():
        field.widget.attrs["autocomplete"] = "current-password" if field is password_form.fields["old_password"] else "new-password"
    return {
        "profile_form": profile_form or SuperAdminProfileForm(instance=request.user),
        "password_form": password_form,
        "system_info": {
            "name": "QuickQueue",
            "description": "Smart Appointment and Queue Management System for Barangays",
            "backend": "Django",
            "database": "PostgreSQL (Supabase)",
            "deployment": "Vercel",
            "timezone": settings.TIME_ZONE,
        },
        "overview": {
            "barangays": Barangay.objects.count(),
            "admins": len(direct_admin_ids | staff_admin_ids),
            "residents": Resident.objects.count(),
            "appointments": Appointment.objects.count(),
        },
    }


@login_required(login_url="signin")
def superadmin_settings(request):
    _require_superuser(request)
    if request.method == "GET":
        return render(request, "superadmin/settings.html", _settings_context(request))

    action = request.POST.get("action")
    if action == "profile":
        profile_form = SuperAdminProfileForm(request.POST, instance=request.user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your profile information was updated successfully.")
            return redirect("superadmin_system_settings")
        return render(
            request,
            "superadmin/settings.html",
            _settings_context(request, profile_form=profile_form),
            status=400,
        )
    if action == "password":
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was changed successfully.")
            return redirect("superadmin_system_settings")
        return render(
            request,
            "superadmin/settings.html",
            _settings_context(request, password_form=password_form),
            status=400,
        )
    messages.error(request, "Unknown settings action.")
    return redirect("superadmin_system_settings")
