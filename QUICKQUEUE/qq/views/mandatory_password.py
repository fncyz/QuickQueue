from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import redirect, render

from qq.models import BarangayStaff


@login_required(login_url="signin")
def mandatory_password_change(request):
    try:
        profile = request.user.staff_profile
    except BarangayStaff.DoesNotExist:
        return redirect("signin")
    if profile.role != BarangayStaff.Role.ADMIN:
        return redirect("staff_dashboard")
    if not profile.must_change_password:
        return redirect("barangay_dashboard")
    form = SetPasswordForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        profile.must_change_password = False
        profile.save(update_fields=("must_change_password", "updated_at"))
        update_session_auth_hash(request, user)
        return redirect("barangay_dashboard")
    return render(request, "qq/mandatory_password_change.html", {"form": form})
