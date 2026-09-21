from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from qq.models import BarangayStaff, Notification, QueueTicket, Service


def _regular_staff(user):
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    return staff


@login_required(login_url="signin")
def staff_completed_documents(request):
    staff = _regular_staff(request.user)
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_queue_history")
    base = QueueTicket.objects.filter(
        appointment__barangay=staff.barangay,
        claim_status=QueueTicket.ClaimStatus.CLAIMED,
    ).select_related("appointment__resident", "appointment__service")
    search = request.GET.get("q", "").strip()
    service = request.GET.get("service", "")
    date_filter = request.GET.get("date", "")
    filtered = base
    if search:
        filtered = filtered.filter(
            Q(queue_number__icontains=search)
            | Q(appointment__resident__first_name__icontains=search)
            | Q(appointment__resident__last_name__icontains=search)
            | Q(appointment__service__name__icontains=search)
        )
    if service.isdigit():
        filtered = filtered.filter(appointment__service_id=int(service))
    if date_filter:
        try:
            filtered = filtered.filter(claimed_at__date=timezone.datetime.strptime(date_filter, "%Y-%m-%d").date())
        except ValueError:
            pass
    today = timezone.localdate()
    return render(request, "barangay_staff/completed_documents.html", {
        "active_page": "completed", "staff": staff, "barangay": staff.barangay,
        "documents": filtered.order_by("-claimed_at", "-updated_at"),
        "total_archived": base.count(), "completed_today": base.filter(claimed_at__date=today).count(),
        "processed_by_you": 0,
        "services": Service.objects.filter(is_active=True).order_by("name"),
        "filters": {"q": search, "service": service, "date": date_filter},
        "unread_notifications": Notification.objects.filter(
            appointment__barangay=staff.barangay, admin_is_read=False
        ).count(),
    })


@login_required(login_url="signin")
def staff_document_preview(request, pk):
    staff = _regular_staff(request.user)
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        raise Http404("This document is available in the staff archive only.")
    ticket = get_object_or_404(
        QueueTicket.objects.select_related("appointment__resident", "appointment__service", "appointment__barangay"),
        pk=pk,
        appointment__barangay=staff.barangay,
        claim_status__in=[
            QueueTicket.ClaimStatus.PROCESSING,
            QueueTicket.ClaimStatus.READY,
            QueueTicket.ClaimStatus.CLAIMED,
        ],
    )
    if request.GET.get("download") == "1":
        resident = ticket.appointment.resident
        content = (
            f"QuickQueue Completed Document\n\nDocument: {ticket.appointment.service.name}\n"
            f"Resident: {resident}\nQueue number: {ticket.queue_number}\n"
            f"Completed: {ticket.claimed_at or ticket.updated_at}\nBarangay: {staff.barangay.name}\n"
        )
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="DOC-{ticket.pk:06d}.txt"'
        return response
    return render(request, "barangay_staff/document_preview.html", {
        "staff": staff, "barangay": staff.barangay, "ticket": ticket,
        "auto_print": request.GET.get("print") == "1",
        "is_archived": ticket.claim_status == QueueTicket.ClaimStatus.CLAIMED,
    })
