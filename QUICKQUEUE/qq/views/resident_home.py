from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect, render


@login_required(login_url="signin")
def resident_home(request):
    """Display the resident dashboard after a successful sign-in."""
    return render(request, "resident/home.html", {"active_page": "home"})


def resident_logout(request):
    """End the resident session and return to sign in."""
    logout(request)
    return redirect("signin")
