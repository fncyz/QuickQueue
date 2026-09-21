from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from qq.models import Barangay, BarangayStaff, Notification, Resident


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
def barangay_residents(request):
    """List and filter residents registered under the staff member's barangay."""
    barangay = _barangay_for(request.user)
    today = timezone.localdate()
    month_start = today.replace(day=1)

    base = Resident.objects.filter(barangay=barangay).select_related("user")

    total_residents = base.count()
    active_residents = base.filter(user__is_active=True).count()
    inactive_residents = base.filter(user__is_active=False).count()
    new_this_month = base.filter(created_at__date__gte=month_start).count()

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    sex = request.GET.get("sex", "").strip()
    sort = request.GET.get("sort", "").strip()
    registered = request.GET.get("registered", "").strip()

    residents = base
    if search:
        residents = residents.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(contact_number__icontains=search)
            | Q(email__icontains=search)
        )
    if status == "active":
        residents = residents.filter(user__is_active=True)
    elif status == "inactive":
        residents = residents.filter(user__is_active=False)
    if sex in dict(Resident.Sex.choices):
        residents = residents.filter(sex=sex)

    if registered == "today":
        residents = residents.filter(created_at__date=today)
    elif registered == "week":
        residents = residents.filter(created_at__date__gte=today - timedelta(days=7))
    elif registered == "month":
        residents = residents.filter(created_at__date__gte=month_start)
    elif registered == "year":
        residents = residents.filter(created_at__date__gte=today.replace(month=1, day=1))

    if sort == "az":
        residents = residents.order_by("last_name", "first_name")
    elif sort == "za":
        residents = residents.order_by("-last_name", "-first_name")
    elif sort == "newest":
        residents = residents.order_by("-created_at")
    elif sort == "oldest":
        residents = residents.order_by("created_at")
    else:
        residents = residents.order_by("last_name", "first_name")

    try:
        per_page = int(request.GET.get("per_page", "10"))
    except ValueError:
        per_page = 10
    if per_page not in (5, 10, 20, 50):
        per_page = 10

    paginator = Paginator(residents, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    for resident in page_obj:
        initials = f"{resident.first_name[:1]}{resident.last_name[:1]}".upper()
        resident.initials = initials
        resident.is_account_active = resident.user.is_active

    return render(
        request,
        "barangay_admin/residents.html",
        {
            "active_page": "residents",
            "barangay": barangay,
            "today": today,
            "stats": {
                "total": total_residents,
                "active": active_residents,
                "inactive": inactive_residents,
                "new_month": new_this_month,
            },
            "residents_page": page_obj,
            "residents_total": paginator.count,
            "per_page": per_page,
            "filters": {
                "q": search,
                "status": status,
                "sex": sex,
                "sort": sort,
                "registered": registered,
            },
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )
