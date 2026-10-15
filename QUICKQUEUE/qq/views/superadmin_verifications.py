from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from qq.models import BarangayAdminRegistration, BarangayStaff
from qq.services.admin_account_service import approve_admin_registration, reject_admin_registration


def _require_superuser(request):
    if not request.user.is_superuser:
        raise PermissionDenied


def _verification_context(request):
    queryset = BarangayAdminRegistration.objects.select_related("user", "barangay")
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", BarangayAdminRegistration.Status.PENDING)
    sort = request.GET.get("sort", "newest")
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search)
            | Q(user__username__icontains=search) | Q(email__icontains=search)
            | Q(barangay__name__icontains=search)
        )
    valid_statuses = {choice[0] for choice in BarangayAdminRegistration.Status.choices}
    if status in valid_statuses:
        queryset = queryset.filter(status=status)
    elif status != "all":
        status = BarangayAdminRegistration.Status.PENDING
        queryset = queryset.filter(status=status)
    queryset = queryset.order_by("created_at" if sort == "oldest" else "-created_at")
    page = Paginator(queryset, 10).get_page(request.GET.get("page"))
    counts = {
        row["status"]: row["total"]
        for row in BarangayAdminRegistration.objects.values("status").annotate(total=Count("id"))
    }
    return {
        "verification_page": page,
        "total_applications": sum(counts.values()),
        "pending_applications": counts.get(BarangayAdminRegistration.Status.PENDING, 0),
        "approved_applications": counts.get(BarangayAdminRegistration.Status.APPROVED, 0),
        "rejected_applications": counts.get(BarangayAdminRegistration.Status.REJECTED, 0),
        "search_query": search,
        "status_filter": status,
        "sort_order": "oldest" if sort == "oldest" else "newest",
    }


@login_required(login_url="signin")
def superadmin_verifications(request):
    _require_superuser(request)
    return render(request, "superadmin/verifications.html", _verification_context(request))


@login_required(login_url="signin")
def superadmin_verification_detail(request, pk):
    _require_superuser(request)
    application = get_object_or_404(
        BarangayAdminRegistration.objects.select_related("user", "barangay"), pk=pk
    )
    existing_admin = application.barangay.user
    if existing_admin is None:
        profile = BarangayStaff.objects.filter(
            barangay=application.barangay, role=BarangayStaff.Role.ADMIN
        ).select_related("user").first()
        existing_admin = profile.user if profile else None
    return render(request, "superadmin/verification_detail.html", {
        "application": application,
        "existing_admin": existing_admin,
    })


@login_required(login_url="signin")
@require_POST
def superadmin_verification_approve(request, pk):
    _require_superuser(request)
    try:
        application = approve_admin_registration(pk)
    except BarangayAdminRegistration.DoesNotExist:
        application = get_object_or_404(BarangayAdminRegistration, pk=pk)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("superadmin_verification_detail", pk=pk)
    messages.success(request, f"The application for Barangay {application.barangay.name} was approved.")
    return redirect("superadmin_verification_detail", pk=pk)


@login_required(login_url="signin")
@require_POST
def superadmin_verification_reject(request, pk):
    _require_superuser(request)
    try:
        application = reject_admin_registration(pk)
    except BarangayAdminRegistration.DoesNotExist:
        application = get_object_or_404(BarangayAdminRegistration, pk=pk)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("superadmin_verification_detail", pk=pk)
    messages.success(request, f"The application for Barangay {application.barangay.name} was rejected.")
    return redirect("superadmin_verification_detail", pk=pk)
