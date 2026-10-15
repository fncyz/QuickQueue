from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from qq.models import BarangayStaff


class MandatoryPasswordChangeMiddleware:
    """Restrict temporary-password admin sessions until a new password is chosen."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.is_superuser:
            try:
                profile = user.staff_profile
            except BarangayStaff.DoesNotExist:
                profile = None
            if profile and profile.role == BarangayStaff.Role.ADMIN and profile.must_change_password:
                allowed = {
                    reverse("signin"),
                    reverse("staff_logout"),
                    reverse("mandatory_password_change"),
                }
                if request.path not in allowed and not request.path.startswith(("/static/", "/media/")):
                    if request.path.startswith("/api/"):
                        return JsonResponse(
                            {"detail": "A password change is required before accessing QuickQueue."},
                            status=403,
                        )
                    return redirect("mandatory_password_change")
        return self.get_response(request)
