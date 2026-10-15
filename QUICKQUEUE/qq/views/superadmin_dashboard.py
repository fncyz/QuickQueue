from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.forms import SuperAdminBarangayForm
from qq.models import Appointment, Barangay, BarangayAdminRegistration, BarangayStaff, Resident

SUPERADMIN_PAGES = {
    "barangays": ("Barangays", "Barangay management will be available in a future phase."),
    "barangay_admins": ("Barangay Admins", "Barangay administrator management will be available in a future phase."),
    "pending_verifications": ("Pending Verifications", "Verification tools will be available in a future phase."),
    "system_settings": ("System Settings", "System configuration will be available in a future phase."),
}


def _require_superuser(request):
    if not request.user.is_superuser:
        raise PermissionDenied


def _appointment_period(value, today):
    if value == "today":
        return today, today, "Today", "today"
    if value == "last_7_days":
        return today - timedelta(days=6), today, "Last 7 Days", "last_7_days"
    if value == "this_year":
        return today.replace(month=1, day=1), today, "This Year", "this_year"
    return today.replace(day=1), today, "This Month", "this_month"


def _recent_activities():
    activities = []
    for barangay in Barangay.objects.only("name", "created_at").order_by("-created_at")[:8]:
        activities.append({
            "kind": "barangay",
            "description": f"Barangay {barangay.name} was registered.",
            "timestamp": barangay.created_at,
        })

    registrations = BarangayAdminRegistration.objects.select_related("barangay", "user").order_by("-created_at")[:8]
    for registration in registrations:
        applicant = registration.user.get_full_name() or registration.user.username
        activities.append({
            "kind": "application",
            "description": f"{applicant} submitted an administrator application for Barangay {registration.barangay.name}.",
            "timestamp": registration.created_at,
        })
        if registration.reviewed_at and registration.status in {
            BarangayAdminRegistration.Status.APPROVED,
            BarangayAdminRegistration.Status.REJECTED,
        }:
            activities.append({
                "kind": registration.status,
                "description": f"The administrator application for Barangay {registration.barangay.name} was {registration.get_status_display().lower()}.",
                "timestamp": registration.reviewed_at,
            })

    return sorted(activities, key=lambda activity: activity["timestamp"], reverse=True)[:8]


@login_required(login_url="signin")
def superadmin_dashboard(request):
    """Display the dedicated portal landing page for Django superusers."""
    _require_superuser(request)
    today = timezone.localdate()
    period_start, period_end, period_label, selected_period = _appointment_period(
        request.GET.get("period", "this_month"), today
    )

    appointment_counts = list(
        Appointment.objects.filter(appointment_date__range=(period_start, period_end))
        .values("barangay__name")
        .annotate(total=Count("id"))
        .order_by("-total", "barangay__name")
    )
    largest_count = max((item["total"] for item in appointment_counts), default=0)
    for item in appointment_counts:
        item["percentage"] = round(item["total"] / largest_count * 100) if largest_count else 0

    direct_admin_ids = set(
        Barangay.objects.exclude(user_id=None).values_list("user_id", flat=True)
    )
    staff_admin_ids = set(
        BarangayStaff.objects.filter(role=BarangayStaff.Role.ADMIN, user__isnull=False)
        .values_list("user_id", flat=True)
    )

    verification_counts = {
        row["status"]: row["total"]
        for row in BarangayAdminRegistration.objects.values("status").annotate(total=Count("id"))
    }
    total_applications = sum(verification_counts.values())
    verification_rows = []
    for status, label in BarangayAdminRegistration.Status.choices:
        count = verification_counts.get(status, 0)
        percentage = round(count / total_applications * 100, 1) if total_applications else 0
        verification_rows.append({
            "status": status,
            "label": label,
            "count": count,
            "percentage": percentage,
            "action": "Awaiting review" if status == BarangayAdminRegistration.Status.PENDING else f"{label} decision recorded",
        })

    context = {
        "today": today,
        "total_barangays": Barangay.objects.count(),
        "total_admins": len(direct_admin_ids | staff_admin_ids),
        "total_residents": Resident.objects.count(),
        "today_appointments": Appointment.objects.filter(appointment_date=today).count(),
        "appointment_counts": appointment_counts,
        "period_label": period_label,
        "selected_period": selected_period,
        "recent_activities": _recent_activities(),
        "total_applications": total_applications,
        "verification_rows": verification_rows,
        "approved_applications": verification_counts.get(BarangayAdminRegistration.Status.APPROVED, 0),
        "rejected_applications": verification_counts.get(BarangayAdminRegistration.Status.REJECTED, 0),
        "pending_applications": verification_counts.get(BarangayAdminRegistration.Status.PENDING, 0),
        "pending_verifications": BarangayAdminRegistration.objects.filter(
            status=BarangayAdminRegistration.Status.PENDING
        ).select_related("barangay", "user").order_by("-created_at")[:5],
    }
    return render(request, "superadmin/dashboard.html", context)


@login_required(login_url="signin")
def superadmin_placeholder(request, page):
    """Display a protected placeholder for a future Super Admin section."""
    _require_superuser(request)
    title, message = SUPERADMIN_PAGES[page]
    return render(request, "superadmin/placeholder.html", {
        "page_title": title,
        "placeholder_message": message,
    })


def _barangay_queryset():
    admin_staff = BarangayStaff.objects.filter(
        role=BarangayStaff.Role.ADMIN,
        is_active=True,
    ).select_related("user").order_by("created_at")
    return Barangay.objects.select_related("user").prefetch_related(
        Prefetch("staff_members", queryset=admin_staff, to_attr="active_admins")
    )


def _administrator_name(barangay):
    if barangay.user_id:
        return barangay.user.get_full_name() or barangay.user.username
    if barangay.active_admins:
        return barangay.active_admins[0].full_name
    return None


def _barangay_management_context(request, *, form=None, editing=None):
    today = timezone.localdate()
    queryset = _barangay_queryset().annotate(
        resident_count=Count("residents", distinct=True),
        staff_count=Count("staff_members", distinct=True),
        today_appointments=Count("appointments", filter=Q(appointments__appointment_date=today), distinct=True),
        completed_today=Count("appointments", filter=Q(appointments__appointment_date=today, appointments__status=Appointment.Status.COMPLETED), distinct=True),
    )
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")
    sort = request.GET.get("sort", "asc")
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(address__icontains=search))
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    else:
        status = "all"
    queryset = queryset.order_by("-name" if sort == "desc" else "name")
    page = Paginator(queryset, 10).get_page(request.GET.get("page"))
    for barangay in page.object_list:
        barangay.assigned_administrator = _administrator_name(barangay)
    selected_id = request.GET.get("selected")
    selected_barangay = next((item for item in page.object_list if str(item.pk) == selected_id), None)
    if selected_barangay is None and page.object_list:
        selected_barangay = page.object_list[0]
    return {
        "barangay_page": page,
        "search_query": search,
        "status_filter": status,
        "sort_order": "desc" if sort == "desc" else "asc",
        "total_barangays": Barangay.objects.count(),
        "active_barangays": Barangay.objects.filter(is_active=True).count(),
        "inactive_barangays": Barangay.objects.filter(is_active=False).count(),
        "active_admins": BarangayStaff.objects.filter(
            role=BarangayStaff.Role.ADMIN, user__is_active=True
        ).values("user_id").distinct().count(),
        "pending_registrations": BarangayAdminRegistration.objects.filter(
            status=BarangayAdminRegistration.Status.PENDING
        ).count(),
        "total_residents": Resident.objects.count(),
        "selected_barangay": selected_barangay,
        "barangay_form": form or SuperAdminBarangayForm(),
        "editing_barangay": editing,
        "show_barangay_modal": form is not None or request.GET.get("add") == "1" or editing is not None,
    }


@login_required(login_url="signin")
def superadmin_barangays(request):
    _require_superuser(request)
    return render(request, "superadmin/barangays.html", _barangay_management_context(request))


@login_required(login_url="signin")
@require_POST
def superadmin_barangay_add(request):
    _require_superuser(request)
    form = SuperAdminBarangayForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                barangay = form.save()
        except IntegrityError:
            form.add_error("name", "A barangay with this name already exists.")
        else:
            messages.success(request, f"Barangay {barangay.name} was added successfully.")
            return redirect("superadmin_barangays")
    return render(request, "superadmin/barangays.html", _barangay_management_context(request, form=form), status=400)


@login_required(login_url="signin")
def superadmin_barangay_detail(request, pk):
    _require_superuser(request)
    barangay = get_object_or_404(_barangay_queryset(), pk=pk)
    barangay.assigned_administrator = _administrator_name(barangay)
    return render(request, "superadmin/barangay_detail.html", {"barangay": barangay})


@login_required(login_url="signin")
def superadmin_barangay_edit(request, pk):
    _require_superuser(request)
    barangay = get_object_or_404(_barangay_queryset(), pk=pk)
    if request.method == "GET":
        return render(
            request,
            "superadmin/barangays.html",
            _barangay_management_context(request, form=SuperAdminBarangayForm(instance=barangay), editing=barangay),
        )

    form = SuperAdminBarangayForm(request.POST, instance=barangay)
    if form.is_valid():
        try:
            with transaction.atomic():
                barangay = form.save()
        except IntegrityError:
            form.add_error("name", "A barangay with this name already exists.")
        else:
            messages.success(request, f"Barangay {barangay.name} was updated successfully.")
            return redirect("superadmin_barangay_detail", pk=barangay.pk)
    return render(
        request,
        "superadmin/barangays.html",
        _barangay_management_context(request, form=form, editing=barangay),
        status=400,
    )


@login_required(login_url="signin")
@require_POST
def superadmin_barangay_status(request, pk):
    _require_superuser(request)
    barangay = get_object_or_404(Barangay, pk=pk)
    requested_status = request.POST.get("status")
    if requested_status not in {"active", "inactive"}:
        raise Http404("Unknown barangay status.")
    barangay.is_active = requested_status == "active"
    barangay.save(update_fields=("is_active", "updated_at"))
    messages.success(request, f"Barangay {barangay.name} is now {requested_status}.")
    return redirect("superadmin_barangay_detail", pk=barangay.pk)
