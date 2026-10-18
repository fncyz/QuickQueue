from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from qq.models import BarangayStaff, Notification, QueueTicket, Service
from qq.services.notification_service import notify_resident


class DocumentPreviewEditForm(forms.Form):
    purpose = forms.CharField(
        label="Purpose", max_length=500, required=False, strip=True,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    sitio = forms.CharField(
        label="Purok / Sitio", max_length=100, required=False, strip=True,
    )


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
    query = request.GET.urlencode()
    destination = "/barangay/staff/documents/?tab=completed"
    if query:
        destination += f"&{query}"
    return redirect(destination)


def completed_documents_context(request, staff):
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
    return {
        "documents": filtered.order_by("-claimed_at", "-updated_at"),
        "total_archived": base.count(), "completed_today": base.filter(claimed_at__date=today).count(),
        "processed_by_you": 0,
        "services": Service.objects.filter(is_active=True).order_by("name"),
        "completed_filters": {"q": search, "service": service, "date": date_filter},
    }


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
    if request.method == "POST" and request.POST.get("action") == "complete":
        with transaction.atomic():
            locked_ticket = get_object_or_404(
                QueueTicket.objects.select_for_update(),
                pk=ticket.pk,
                appointment__barangay=staff.barangay,
            )
            if locked_ticket.claim_status == QueueTicket.ClaimStatus.READY:
                changed = False
            elif locked_ticket.claim_status == QueueTicket.ClaimStatus.PROCESSING:
                locked_ticket.claim_status = QueueTicket.ClaimStatus.READY
                locked_ticket.save(update_fields=["claim_status", "updated_at"])
                notify_resident(
                    appointment=ticket.appointment,
                    notification_type=Notification.NotificationType.DOCUMENT_UPDATE,
                    title="Document Ready for Pickup",
                    message=(
                        "Your requested document has been processed and is now ready "
                        "for pickup at your barangay office."
                    ),
                    event_key=f"ticket:{locked_ticket.pk}:document-ready",
                )
                changed = True
            else:
                return JsonResponse(
                    {"ok": False, "error": "This document is not eligible for completion."},
                    status=409,
                )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "changed": changed, "status": "ready"})
        return redirect(reverse("staff_processing_document_preview", args=[ticket.pk]))
    edit_form = DocumentPreviewEditForm(
        request.POST or None,
        initial={
            "purpose": ticket.appointment.purpose,
            "sitio": ticket.appointment.sitio,
        },
    )
    if request.method == "POST" and edit_form.is_valid():
        appointment = ticket.appointment
        appointment.purpose = edit_form.cleaned_data["purpose"]
        appointment.sitio = edit_form.cleaned_data["sitio"]
        appointment.save(update_fields=["purpose", "sitio", "updated_at"])
        preview_url = reverse("staff_processing_document_preview", args=[ticket.pk])
        if request.GET.get("embedded") == "1":
            preview_url += "?embedded=1"
        return redirect(preview_url)
    if request.GET.get("download") == "1":
        resident = ticket.appointment.resident
        content = (
            f"QuickQueue Completed Document\n\nDocument: {ticket.appointment.service.name}\n"
            f"Resident: {resident}\nQueue number: {ticket.queue_number}\n"
            f"Purok / Sitio: {ticket.appointment.sitio or 'Not provided'}\n"
            f"Purpose: {ticket.appointment.purpose or 'Official purposes'}\n"
            f"Completed: {ticket.claimed_at or ticket.updated_at}\nBarangay: {staff.barangay.name}\n"
        )
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="DOC-{ticket.pk:06d}.txt"'
        return response
    return render(request, "barangay_staff/document_preview.html", {
        "staff": staff, "barangay": staff.barangay, "ticket": ticket,
        "auto_print": request.GET.get("print") == "1",
        "embedded": request.GET.get("embedded") == "1",
        "edit_mode": request.method == "POST" or request.GET.get("edit") == "1",
        "edit_form": edit_form,
        "can_complete": ticket.claim_status == QueueTicket.ClaimStatus.PROCESSING,
        "is_ready": ticket.claim_status == QueueTicket.ClaimStatus.READY,
        "is_archived": ticket.claim_status == QueueTicket.ClaimStatus.CLAIMED,
    })
