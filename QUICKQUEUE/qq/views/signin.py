from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from qq.models import BarangayStaff


def signin(request):
    """Authenticate a registered resident with Django's database-backed auth."""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user is not None:
            login(request, user)
            if user.is_staff and hasattr(user, "barangay_profile"):
                return redirect("barangay_dashboard")
            if hasattr(user, "staff_profile"):
                if user.staff_profile.role == BarangayStaff.Role.ADMIN:
                    return redirect("barangay_dashboard")
                return redirect("staff_dashboard")
            return render(
                request,
                "qq/signin.html",
                {"signin_error": "Resident access is available in the QuickQueue mobile app."},
            )
        return render(
            request,
            "qq/signin.html",
            {"signin_error": "Invalid username or password."},
        )

    return render(request, "qq/signin.html")


def staff_logout(request):
    """End a staff or barangay administrator session."""
    logout(request)
    return redirect("signin")
