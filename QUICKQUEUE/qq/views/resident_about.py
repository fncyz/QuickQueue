from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url="signin")
def resident_about(request):
    """Display the QuickQueue and school information page."""
    return render(request, "resident/about.html", {"active_page": "about"})
