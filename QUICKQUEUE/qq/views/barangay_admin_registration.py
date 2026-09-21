from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.shortcuts import render
from django.utils import timezone

from qq.models import Barangay, BarangayAdminRegistration


def barangay_admin_registration(request):
    barangays = Barangay.objects.filter(is_active=True, user__isnull=True).order_by("name")
    context = {"barangays": barangays, "form_data": request.POST}

    if request.method != "POST":
        return render(request, "qq/barangay_admin_registration.html", context)

    fields = {
        "Barangay": request.POST.get("barangay", "").strip(),
        "Municipality": request.POST.get("municipality", "").strip(),
        "Province": request.POST.get("province", "").strip(),
        "Complete address": request.POST.get("complete_address", "").strip(),
        "Zip code": request.POST.get("zip_code", "").strip(),
        "Username": request.POST.get("username", "").strip(),
        "Contact number": request.POST.get("contact_number", "").strip(),
        "Email address": request.POST.get("email", "").strip(),
        "Password": request.POST.get("password", ""),
    }
    errors = [f"{label} is required." for label, value in fields.items() if not value]
    if fields["Password"] and fields["Password"] != request.POST.get("confirm_password", ""):
        errors.append("Passwords do not match.")
    if not request.POST.get("terms"):
        errors.append("You must agree to the Terms and Privacy Policy.")
    if User.objects.filter(username__iexact=fields["Username"]).exists():
        errors.append("Username is already taken.")
    if User.objects.filter(email__iexact=fields["Email address"]).exists():
        errors.append("Email address is already registered.")

    try:
        barangay = barangays.get(pk=fields["Barangay"])
    except (Barangay.DoesNotExist, ValueError):
        barangay = None
        if fields["Barangay"]:
            errors.append("Choose an available barangay.")

    if errors:
        context["errors"] = errors
        return render(request, "qq/barangay_admin_registration.html", context)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=fields["Username"],
                email=fields["Email address"],
                password=fields["Password"],
                is_active=False,
            )
            BarangayAdminRegistration.objects.create(
                user=user,
                barangay=barangay,
                municipality=fields["Municipality"],
                province=fields["Province"],
                complete_address=fields["Complete address"],
                zip_code=fields["Zip code"],
                contact_number=fields["Contact number"],
                email=fields["Email address"],
                terms_accepted_at=timezone.now(),
            )
    except IntegrityError:
        context["errors"] = ["This registration could not be submitted. Please try another username or email address."]
        return render(request, "qq/barangay_admin_registration.html", context)

    return render(request, "qq/barangay_admin_registration.html", {"submitted": True})
