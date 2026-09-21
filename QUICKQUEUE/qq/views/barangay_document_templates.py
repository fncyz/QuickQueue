from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from qq.models import Barangay, BarangayStaff, Notification, Service


@login_required(login_url="signin")
def barangay_document_templates(request):
    try:
        barangay = request.user.barangay_profile
    except Barangay.DoesNotExist:
        try:
            staff = request.user.staff_profile
        except BarangayStaff.DoesNotExist as error:
            raise Http404("This account is not assigned to a barangay.") from error
        if staff.role != BarangayStaff.Role.ADMIN:
            return redirect("staff_document_processing")
        barangay = staff.barangay
    return render(request, "barangay_admin/document_templates.html", {
        "active_page": "templates", "barangay": barangay, "today": timezone.localdate(),
        "services": Service.objects.filter(is_active=True).order_by("name"),
        "unread_notifications": Notification.objects.filter(appointment__barangay=barangay, admin_is_read=False).count(),
    })
