from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from qq.forms import AdministrativePasswordResetForm, BarangayAdminCreateForm, BarangayAdminEditForm
from qq.models import Appointment, Barangay, BarangayAdminRegistration, BarangayStaff, Resident
from django.utils import timezone
from qq.services.admin_account_service import create_barangay_admin, reset_admin_password, update_barangay_admin


def _require_superuser(request):
    if not request.user.is_superuser:
        raise PermissionDenied


def _admin_queryset():
    return User.objects.filter(
        Q(barangay_profile__isnull=False) | Q(staff_profile__role=BarangayStaff.Role.ADMIN),
        is_superuser=False,
    ).select_related("barangay_profile", "staff_profile__barangay").distinct()


def _barangay_for(user):
    if hasattr(user, "barangay_profile"):
        return user.barangay_profile
    if hasattr(user, "staff_profile") and user.staff_profile.role == BarangayStaff.Role.ADMIN:
        return user.staff_profile.barangay
    return None


def _management_context(request, *, form=None, editing=None):
    queryset = _admin_queryset()
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")
    barangay_id = request.GET.get("barangay", "")
    sort = request.GET.get("sort", "asc")
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search)
            | Q(username__icontains=search) | Q(email__icontains=search)
            | Q(barangay_profile__name__icontains=search)
            | Q(staff_profile__barangay__name__icontains=search)
        )
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    else:
        status = "all"
    if barangay_id.isdigit():
        queryset = queryset.filter(
            Q(barangay_profile__pk=barangay_id) | Q(staff_profile__barangay_id=barangay_id)
        )
    else:
        barangay_id = ""
    queryset = queryset.order_by("-first_name", "-last_name", "-username") if sort == "desc" else queryset.order_by("first_name", "last_name", "username")
    page = Paginator(queryset, 10).get_page(request.GET.get("page"))
    for admin_user in page.object_list:
        admin_user.assigned_barangay = _barangay_for(admin_user)
        admin_user.contact_number = getattr(getattr(admin_user, "staff_profile", None), "contact_number", "")
    selected_id = request.GET.get("selected")
    selected_admin = next((item for item in page.object_list if str(item.pk) == selected_id), None)
    if selected_admin is None and page.object_list:
        selected_admin = page.object_list[0]
    selected_stats = None
    if selected_admin and selected_admin.assigned_barangay:
        barangay = selected_admin.assigned_barangay
        today = timezone.localdate()
        selected_stats = {
            "residents": Resident.objects.filter(barangay=barangay).count(),
            "staff": BarangayStaff.objects.filter(barangay=barangay).exclude(role=BarangayStaff.Role.ADMIN).count(),
            "appointments": Appointment.objects.filter(barangay=barangay, appointment_date=today).count(),
            "completed": Appointment.objects.filter(
                barangay=barangay, appointment_date=today, status=Appointment.Status.COMPLETED
            ).count(),
        }

    all_admins = _admin_queryset()
    assigned_ids = set(Barangay.objects.exclude(user_id=None).values_list("id", flat=True))
    assigned_ids.update(BarangayStaff.objects.filter(role=BarangayStaff.Role.ADMIN).values_list("barangay_id", flat=True))
    return {
        "admin_page": page,
        "total_admins": all_admins.count(),
        "active_admins": all_admins.filter(is_active=True).count(),
        "inactive_admins": all_admins.filter(is_active=False).count(),
        "unassigned_barangays": Barangay.objects.exclude(pk__in=assigned_ids).count(),
        "pending_registrations": BarangayAdminRegistration.objects.filter(
            status=BarangayAdminRegistration.Status.PENDING
        ).count(),
        "selected_admin": selected_admin,
        "selected_stats": selected_stats,
        "barangays": Barangay.objects.order_by("name"),
        "search_query": search,
        "status_filter": status,
        "barangay_filter": barangay_id,
        "sort_order": "desc" if sort == "desc" else "asc",
        "admin_form": form or BarangayAdminCreateForm(),
        "editing_admin": editing,
        "show_admin_modal": form is not None or request.GET.get("add") == "1" or editing is not None,
    }


@login_required(login_url="signin")
def superadmin_admins(request):
    _require_superuser(request)
    return render(request, "superadmin/admins.html", _management_context(request))


@login_required(login_url="signin")
@require_POST
def superadmin_admin_add(request):
    _require_superuser(request)
    form = BarangayAdminCreateForm(request.POST)
    if form.is_valid():
        try:
            user, _ = create_barangay_admin(form.cleaned_data)
        except (IntegrityError, ValueError) as error:
            form.add_error(None, str(error) or "The administrator account could not be created.")
        else:
            messages.success(request, f"Administrator {user.username} was registered successfully.")
            return redirect("superadmin_barangay_admins")
    return render(request, "superadmin/admins.html", _management_context(request, form=form), status=400)


@login_required(login_url="signin")
def superadmin_admin_detail(request, pk):
    _require_superuser(request)
    admin_user = get_object_or_404(_admin_queryset(), pk=pk)
    admin_user.assigned_barangay = _barangay_for(admin_user)
    return render(request, "superadmin/admin_detail.html", {"admin_account": admin_user})


@login_required(login_url="signin")
def superadmin_admin_edit(request, pk):
    _require_superuser(request)
    admin_user = get_object_or_404(_admin_queryset(), pk=pk)
    if request.method == "GET":
        form = BarangayAdminEditForm(user=admin_user)
        return render(request, "superadmin/admins.html", _management_context(request, form=form, editing=admin_user))
    form = BarangayAdminEditForm(request.POST, user=admin_user)
    if form.is_valid():
        try:
            update_barangay_admin(admin_user, form.cleaned_data)
        except (IntegrityError, ValueError) as error:
            form.add_error("barangay", str(error) or "The account could not be updated.")
        else:
            messages.success(request, f"Administrator {admin_user.username} was updated successfully.")
            return redirect("superadmin_admin_detail", pk=admin_user.pk)
    return render(request, "superadmin/admins.html", _management_context(request, form=form, editing=admin_user), status=400)


@login_required(login_url="signin")
@require_POST
def superadmin_admin_status(request, pk):
    _require_superuser(request)
    admin_user = get_object_or_404(_admin_queryset(), pk=pk)
    if hasattr(admin_user, "resident_profile"):
        messages.error(request, "This account also belongs to a resident and cannot be disabled here.")
        return redirect("superadmin_admin_detail", pk=admin_user.pk)
    requested_status = request.POST.get("status")
    if requested_status not in {"active", "inactive"}:
        raise Http404("Unknown administrator status.")
    active = requested_status == "active"
    admin_user.is_active = active
    admin_user.save(update_fields=("is_active",))
    if hasattr(admin_user, "staff_profile"):
        admin_user.staff_profile.is_active = active
        admin_user.staff_profile.save(update_fields=("is_active", "updated_at"))
    messages.success(request, f"Administrator {admin_user.username} is now {'active' if active else 'inactive'}.")
    return redirect("superadmin_admin_detail", pk=admin_user.pk)


@login_required(login_url="signin")
@require_POST
def superadmin_admin_password_reset(request, pk):
    _require_superuser(request)
    admin_user = get_object_or_404(_admin_queryset(), pk=pk)
    if not admin_user.email:
        messages.error(request, "A password reset cannot be sent because this account has no email address.")
        return redirect("superadmin_admin_detail", pk=admin_user.pk)
    form = PasswordResetForm({"email": admin_user.email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            email_template_name="superadmin/emails/admin_password_reset.txt",
            subject_template_name="superadmin/emails/admin_password_reset_subject.txt",
        )
        messages.success(request, f"A secure password-reset link was sent to {admin_user.email}.")
    return redirect("superadmin_admin_detail", pk=admin_user.pk)


@login_required(login_url="signin")
@require_POST
def superadmin_admin_temporary_password(request, pk):
    _require_superuser(request)
    admin_user = get_object_or_404(_admin_queryset(), pk=pk)
    form = AdministrativePasswordResetForm(
        request.POST, superuser=request.user, target_user=admin_user
    )
    if form.is_valid():
        reset_admin_password(admin_user, form.cleaned_data["temporary_password1"])
        messages.success(
            request,
            f"A temporary password was assigned to {admin_user.username}. Existing sessions were ended.",
        )
        return redirect("superadmin_admin_detail", pk=admin_user.pk)
    admin_user.assigned_barangay = _barangay_for(admin_user)
    return render(request, "superadmin/admin_detail.html", {
        "admin_account": admin_user,
        "reset_form": form,
        "show_reset_modal": True,
    }, status=400)
