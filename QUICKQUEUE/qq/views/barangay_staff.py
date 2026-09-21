from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Barangay, BarangayStaff, Notification


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


def _staff_queryset(barangay):
    return BarangayStaff.objects.filter(barangay=barangay).select_related("user")


@login_required(login_url="signin")
def barangay_staff(request):
    """List and filter barangay staff accounts for the signed-in barangay."""
    barangay = _barangay_for(request.user)
    today = timezone.localdate()

    base = _staff_queryset(barangay)
    total_staff = base.count()
    active_staff = base.filter(is_active=True).count()
    inactive_staff = base.filter(is_active=False).count()

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    role = request.GET.get("role", "").strip()

    staff_list = base
    if search:
        staff_list = staff_list.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(contact_number__icontains=search)
        )
    if status == "active":
        staff_list = staff_list.filter(is_active=True)
    elif status == "inactive":
        staff_list = staff_list.filter(is_active=False)
    if role in dict(BarangayStaff.Role.choices):
        staff_list = staff_list.filter(role=role)

    staff_list = staff_list.order_by("last_name", "first_name")

    try:
        per_page = int(request.GET.get("per_page", "10"))
    except ValueError:
        per_page = 10
    if per_page not in (5, 10, 20, 50):
        per_page = 10

    paginator = Paginator(staff_list, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "barangay_admin/staff.html",
        {
            "active_page": "staff",
            "barangay": barangay,
            "today": today,
            "stats": {
                "total": total_staff,
                "active": active_staff,
                "inactive": inactive_staff,
            },
            "staff_page": page_obj,
            "staff_total": paginator.count,
            "per_page": per_page,
            "filters": {
                "q": search,
                "status": status,
                "role": role,
            },
            "role_choices": BarangayStaff.Role.choices,
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )


@login_required(login_url="signin")
@require_POST
def barangay_staff_add(request):
    """Create a new barangay staff member (and linked login user)."""
    barangay = _barangay_for(request.user)

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    contact_number = request.POST.get("contact_number", "").strip()
    role = request.POST.get("role", BarangayStaff.Role.STAFF).strip()
    password = request.POST.get("password", "").strip()
    confirm_password = request.POST.get("confirm_password", "").strip()
    is_active = request.POST.get("is_active") == "on"

    if role not in dict(BarangayStaff.Role.choices):
        role = BarangayStaff.Role.STAFF

    if not first_name or not last_name or not username or not password or not contact_number:
        return redirect("barangay_staff")

    if password != confirm_password:
        return redirect("barangay_staff")

    if len(password) < 6:
        return redirect("barangay_staff")

    if User.objects.filter(username=username).exists():
        return redirect("barangay_staff")

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_active=is_active,
        )
        BarangayStaff.objects.create(
            barangay=barangay,
            user=user,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            username=username,
            email=email,
            contact_number=contact_number,
            role=role,
            is_active=is_active,
        )

    return redirect("barangay_staff")


@login_required(login_url="signin")
@require_POST
def barangay_staff_edit(request, pk):
    """Update an existing barangay staff member."""
    barangay = _barangay_for(request.user)
    staff = get_object_or_404(BarangayStaff, pk=pk, barangay=barangay)

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    email = request.POST.get("email", "").strip()
    contact_number = request.POST.get("contact_number", "").strip()
    role = request.POST.get("role", staff.role).strip()
    is_active = request.POST.get("is_active") == "on"
    password = request.POST.get("password", "").strip()

    if not first_name or not last_name:
        return redirect("barangay_staff")
    if role not in dict(BarangayStaff.Role.choices):
        role = staff.role

    staff.first_name = first_name
    staff.last_name = last_name
    staff.middle_name = middle_name
    staff.email = email
    staff.contact_number = contact_number
    staff.role = role
    staff.is_active = is_active
    staff.save()

    if staff.user_id:
        user = staff.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_active = is_active
        if password:
            user.set_password(password)
        user.save()

    return redirect("barangay_staff")
