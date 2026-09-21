from datetime import date

from django.shortcuts import render

from qq.models import Barangay
from qq.services.res_services import create_resident


def signup(request):
    """Create a resident account and reveal its generated password once."""
    barangays = Barangay.objects.filter(is_active=True).order_by("name")

    if request.method != "POST":
        return render(request, "qq/signup.html", {"barangays": barangays})

    required_fields = {
        "First name": request.POST.get("first_name", "").strip(),
        "Last name": request.POST.get("last_name", "").strip(),
        "Birthdate": request.POST.get("birthdate", "").strip(),
        "Sex": request.POST.get("sex", "").strip(),
        "Username": request.POST.get("username", "").strip(),
        "Contact number": request.POST.get("contact_number", "").strip(),
        "Barangay": request.POST.get("barangay", "").strip(),
    }
    errors = [f"{label} is required." for label, value in required_fields.items() if not value]

    if not request.POST.get("terms"):
        errors.append("You must agree to the Terms and Privacy Policy.")

    if required_fields["Contact number"] and not required_fields["Contact number"].isdigit():
        errors.append("Contact number must contain digits only.")

    birthdate = None
    if required_fields["Birthdate"]:
        try:
            birthdate = date.fromisoformat(required_fields["Birthdate"])
            if birthdate >= date.today():
                errors.append("Birthdate must be in the past.")
        except ValueError:
            errors.append("Enter a valid birthdate.")

    barangay = None
    if required_fields["Barangay"]:
        try:
            barangay = barangays.get(pk=required_fields["Barangay"])
        except (Barangay.DoesNotExist, ValueError):
            errors.append("Choose an active barangay.")

    context = {"barangays": barangays, "errors": errors, "form_data": request.POST}
    if errors:
        return render(request, "qq/signup.html", context)

    try:
        _, username, password = create_resident(
            username=required_fields["Username"],
            first_name=required_fields["First name"],
            middle_name=request.POST.get("middle_name", "").strip(),
            last_name=required_fields["Last name"],
            suffix=request.POST.get("suffix", "").strip(),
            birthdate=birthdate,
            sex=required_fields["Sex"],
            email=request.POST.get("email", "").strip() or None,
            contact_number=required_fields["Contact number"],
            province="Cebu",
            municipality="Toledo City",
            barangay=barangay,
        )
    except ValueError as error:
        context["errors"] = [str(error)]
        return render(request, "qq/signup.html", context)

    return render(
        request,
        "qq/signin.html",
        {"created_credentials": {"username": username, "password": password}},
    )
