from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Appointment, BarangayStaff, Notification, QueueTicket, Service


def _staff_for(user):
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    return staff


@login_required(login_url="signin")
def staff_document_processing(request):
    staff = _staff_for(request.user)
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_queue_history")
    base = QueueTicket.objects.filter(
        appointment__barangay=staff.barangay,
        appointment__status__in=[
            Appointment.Status.CONFIRMED, Appointment.Status.ONGOING, Appointment.Status.COMPLETED,
        ],
    ).exclude(claim_status=QueueTicket.ClaimStatus.CLAIMED).select_related(
        "appointment__resident", "appointment__service", "appointment__time_slot"
    )
    search = request.GET.get("q", "").strip()
    service = request.GET.get("service", "")
    date_filter = request.GET.get("date", "")
    status_filter = request.GET.get("status", "")
    filtered = base
    if search:
        filtered = filtered.filter(
            Q(appointment__resident__first_name__icontains=search)
            | Q(appointment__resident__last_name__icontains=search)
            | Q(queue_number__icontains=search)
            | Q(appointment__service__name__icontains=search)
        )
    if service.isdigit():
        filtered = filtered.filter(appointment__service_id=int(service))
    if date_filter:
        try:
            filtered = filtered.filter(
                appointment__appointment_date=timezone.datetime.strptime(date_filter, "%Y-%m-%d").date()
            )
        except ValueError:
            pass
    if status_filter and status_filter in dict(QueueTicket.ClaimStatus.choices):
        filtered = filtered.filter(claim_status=status_filter)
    return render(request, "barangay_staff/document_processing.html", {
        "active_page": "documents", "staff": staff, "barangay": staff.barangay,
        "tickets": filtered.order_by("appointment__appointment_date", "appointment__time_slot__start_time"),
        "total_count": base.count(),
        "waiting_count": base.filter(claim_status=QueueTicket.ClaimStatus.NONE).count(),
        "processing_count": base.filter(claim_status=QueueTicket.ClaimStatus.PROCESSING).count(),
        "ready_count": base.filter(claim_status=QueueTicket.ClaimStatus.READY).count(),
        "services": Service.objects.filter(is_active=True).order_by("name"),
        "filters": {"q": search, "service": service, "date": date_filter, "status": status_filter},
        "unread_notifications": Notification.objects.filter(
            appointment__barangay=staff.barangay, admin_is_read=False
        ).count(),
    })


@login_required(login_url="signin")
@require_POST
def staff_document_action(request, pk):
    staff = _staff_for(request.user)
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        raise Http404("This action is available to barangay staff accounts only.")
    ticket = get_object_or_404(
        QueueTicket.objects.select_related("appointment__resident", "appointment__service"),
        pk=pk, appointment__barangay=staff.barangay,
    )
    action = request.POST.get("action")
    if action == "start" and ticket.claim_status == QueueTicket.ClaimStatus.NONE:
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        messages.success(request, f"Started processing {ticket.queue_number}.")
    elif action == "ready" and ticket.claim_status == QueueTicket.ClaimStatus.PROCESSING:
        ticket.claim_status = QueueTicket.ClaimStatus.READY
        ticket.save(update_fields=["claim_status", "updated_at"])
        Notification.objects.create(
            resident=ticket.appointment.resident, appointment=ticket.appointment,
            notification_type=Notification.NotificationType.QUEUE_UPDATE,
            title="Document Ready for Claiming",
            message=f"Your {ticket.appointment.service.name} document is ready for claiming.",
        )
        messages.success(request, f"{ticket.queue_number} is ready for claiming.")
    elif action == "archive" and ticket.claim_status in (
        QueueTicket.ClaimStatus.PROCESSING,
        QueueTicket.ClaimStatus.READY,
    ):
        ticket.claim_status = QueueTicket.ClaimStatus.CLAIMED
        ticket.claimed_at = timezone.now()
        ticket.save(update_fields=["claim_status", "claimed_at", "updated_at"])
        if ticket.appointment.status != Appointment.Status.COMPLETED:
            ticket.appointment.status = Appointment.Status.COMPLETED
            ticket.appointment.save(update_fields=["status", "updated_at"])
        Notification.objects.create(
            resident=ticket.appointment.resident,
            appointment=ticket.appointment,
            notification_type=Notification.NotificationType.APPOINTMENT_COMPLETED,
            title="Document Processing Completed",
            message=(
                f"Your {ticket.appointment.service.name} transaction has been completed "
                "and the document has been archived."
            ),
        )
        messages.success(request, f"Completed and archived {ticket.queue_number}.")
    else:
        messages.error(request, "That document action is not available.")
    return redirect("staff_document_processing")
