from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from qq.models import BarangayStaff, Notification
from qq.views.barangay_settings import _update_password, _update_profile


@login_required(login_url="signin")
def staff_settings(request):
    try:
        staff = request.user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_settings")
    active_tab = request.GET.get("tab", "profile")
    if active_tab not in {"profile", "password"}:
        active_tab = "profile"
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "password":
            _update_password(request)
            active_tab = "password"
        else:
            _update_profile(request, staff)
            active_tab = "profile"
        return redirect(f"/barangay/staff/settings/?tab={active_tab}")
    return render(request, "barangay_staff/settings.html", {
        "active_page": "settings", "active_tab": active_tab,
        "staff": staff, "barangay": staff.barangay,
        "unread_notifications": Notification.objects.filter(
            appointment__barangay=staff.barangay, admin_is_read=False
        ).count(),
    })
