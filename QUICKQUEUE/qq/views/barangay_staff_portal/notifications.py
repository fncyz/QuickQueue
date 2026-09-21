import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from qq.models import BarangayStaff, Notification, QueueTicket


def _staff(user):
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    if hasattr(user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        raise Http404("This notification menu is available to regular staff only.")
    return staff


@login_required(login_url="signin")
@require_http_methods(["GET", "POST"])
def staff_document_notifications(request):
    staff = _staff(request.user)
    ready = QueueTicket.objects.filter(
        appointment__barangay=staff.barangay,
        claim_status=QueueTicket.ClaimStatus.READY,
    ).select_related("appointment__resident", "appointment__service")

    if request.method == "POST":
        try:
            ticket_id = json.loads(request.body or "{}").get("ticket_id")
        except json.JSONDecodeError:
            ticket_id = None
        ticket = get_object_or_404(ready, pk=ticket_id)
        already_sent = Notification.objects.filter(
            appointment=ticket.appointment,
            notification_type=Notification.NotificationType.QUEUE_UPDATE,
            title="Document Ready for Claiming",
        ).exists()
        if not already_sent:
            Notification.objects.create(
                resident=ticket.appointment.resident,
                appointment=ticket.appointment,
                notification_type=Notification.NotificationType.QUEUE_UPDATE,
                title="Document Ready for Claiming",
                message=(
                    f"Good day, {ticket.appointment.resident}. Your "
                    f"{ticket.appointment.service.name} is ready to claim at "
                    f"Barangay {staff.barangay.name}. Please bring a valid ID."
                ),
            )
        return JsonResponse({"ok": True, "already_sent": already_sent})

    sent_ids = set(Notification.objects.filter(
        appointment__queue_ticket__in=ready,
        notification_type=Notification.NotificationType.QUEUE_UPDATE,
        title="Document Ready for Claiming",
    ).values_list("appointment_id", flat=True))
    items = []
    for ticket in ready:
        if ticket.appointment_id in sent_ids:
            continue
        resident = ticket.appointment.resident
        items.append({
            "ticket_id": ticket.pk,
            "resident": str(resident),
            "contact": resident.contact_number,
            "service": ticket.appointment.service.name,
            "document_id": f"DOC-{ticket.appointment.created_at.year}-{ticket.appointment_id:05d}",
            "barangay": staff.barangay.name,
        })
    return JsonResponse({"items": items})
