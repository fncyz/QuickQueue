from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

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


@login_required(login_url="signin")
def barangay_notifications(request):
    barangay = _barangay_for(request.user)
    notifications = Notification.objects.filter(
        appointment__barangay=barangay,
    ).select_related("resident", "appointment").order_by("-created_at")

    if request.method == "POST":
        updated = notifications.filter(admin_is_read=False).update(admin_is_read=True)
        messages.success(request, f"Marked {updated} notification{'s' if updated != 1 else ''} as read.")
        return redirect("barangay_notifications")

    return render(request, "barangay_admin/notifications.html", {
        "barangay": barangay,
        "today": timezone.localdate(),
        "notifications": notifications[:100],
        "unread_notifications": notifications.filter(admin_is_read=False).count(),
    })
