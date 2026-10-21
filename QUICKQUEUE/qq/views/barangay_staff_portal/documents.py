from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Appointment, BarangayStaff, Notification, QueueTicket, Service
from qq.views.barangay_staff_portal.completed_documents import completed_documents_context
from qq.services.notification_service import notify_resident
from qq.services.appointment_expiration import (
    expire_overdue_appointments,
    is_appointment_expired,
)


def _is_expired_document(ticket, *, at=None):
    if ticket.appointment.status == Appointment.Status.MISSED:
        return True
    return is_appointment_expired(ticket.appointment, at=at, ticket=ticket)


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
    active_tab = request.GET.get("tab", "processing")
    if active_tab not in {"processing", "completed"}:
        active_tab = "processing"
    expire_overdue_appointments(barangay=staff.barangay)
    base = QueueTicket.objects.filter(
        appointment__barangay=staff.barangay,
        appointment__service__is_temporary=False,
        appointment__status__in=[
            Appointment.Status.CONFIRMED, Appointment.Status.ONGOING,
            Appointment.Status.COMPLETED, Appointment.Status.MISSED,
        ],
    ).exclude(claim_status=QueueTicket.ClaimStatus.CLAIMED).select_related(
        "appointment__resident", "appointment__service", "appointment__time_slot", "served_by"
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
    tickets = list(filtered.order_by(
        "appointment__appointment_date", "appointment__time_slot__start_time"
    ))
    now = timezone.now()
    for ticket in tickets:
        ticket.is_expired = _is_expired_document(ticket, at=now)
        ticket.can_process = ticket.served_by_id == staff.pk
        ticket.can_start = (
            not ticket.is_expired
            and ticket.appointment.status == Appointment.Status.CONFIRMED
            and ticket.status == QueueTicket.Status.WAITING
            and ticket.claim_status == QueueTicket.ClaimStatus.NONE
            and ticket.served_by_id in (None, staff.pk)
        )
    context = {
        "active_page": "documents", "staff": staff, "barangay": staff.barangay,
        "document_tab": active_tab,
        "tickets": tickets,
        "total_count": base.count(),
        "waiting_count": base.filter(claim_status=QueueTicket.ClaimStatus.NONE).count(),
        "processing_count": base.filter(claim_status=QueueTicket.ClaimStatus.PROCESSING).count(),
        "ready_count": base.filter(claim_status=QueueTicket.ClaimStatus.READY).count(),
        "services": Service.objects.filter(
            is_active=True, is_temporary=False,
        ).order_by("name"),
        "filters": {"q": search, "service": service, "date": date_filter, "status": status_filter},
    }
    if active_tab == "completed":
        context.update(completed_documents_context(request, staff))
    return render(request, "barangay_staff/document_processing.html", context)


@login_required(login_url="signin")
@require_POST
def staff_document_action(request, pk):
    staff = _staff_for(request.user)
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        raise Http404("This action is available to barangay staff accounts only.")
    action = request.POST.get("action")
    expire_overdue_appointments(barangay=staff.barangay)
    ticket = get_object_or_404(
        QueueTicket.objects.select_related("appointment__resident", "appointment__service", "appointment__time_slot"),
        pk=pk,
        appointment__barangay=staff.barangay,
        appointment__service__is_temporary=False,
    )
    if action == "archive_expired":
        with transaction.atomic():
            locked_ticket = get_object_or_404(
                QueueTicket.objects.select_for_update().select_related("appointment"),
                pk=ticket.pk,
                appointment__barangay=staff.barangay,
                appointment__service__is_temporary=False,
            )
            if (
                locked_ticket.appointment.status not in (Appointment.Status.CONFIRMED, Appointment.Status.PENDING)
                or not is_appointment_expired(locked_ticket.appointment, ticket=locked_ticket)
            ):
                messages.error(request, "Only overdue, unfinished appointments can be archived.")
                return redirect("staff_document_processing")
            appointment = locked_ticket.appointment
            appointment.status = Appointment.Status.MISSED
            appointment.save(update_fields=["status", "updated_at"])
            locked_ticket.status = QueueTicket.Status.MISSED
            locked_ticket.save(update_fields=["status", "updated_at"])
        messages.success(
            request,
            f"Archived expired appointment {ticket.queue_number}. Its records remain available in history.",
        )
    elif action == "start":
        with transaction.atomic():
            locked_ticket = get_object_or_404(
                QueueTicket.objects.select_for_update().select_related("appointment__time_slot"),
                pk=ticket.pk,
                appointment__barangay=staff.barangay,
                appointment__service__is_temporary=False,
            )
            appointment = locked_ticket.appointment
            if locked_ticket.served_by_id not in (None, staff.pk):
                messages.error(request, "This document is assigned to another staff member.")
                return redirect("staff_document_processing")
            if (
                is_appointment_expired(appointment, ticket=locked_ticket)
                or appointment.status != Appointment.Status.CONFIRMED
                or locked_ticket.status != QueueTicket.Status.WAITING
                or locked_ticket.claim_status != QueueTicket.ClaimStatus.NONE
            ):
                if is_appointment_expired(appointment, ticket=locked_ticket):
                    appointment.status = Appointment.Status.MISSED
                    appointment.save(update_fields=["status", "updated_at"])
                    locked_ticket.status = QueueTicket.Status.MISSED
                    locked_ticket.save(update_fields=["status", "updated_at"])
                    message = "This appointment has expired and cannot be processed."
                else:
                    message = "This document is no longer eligible for processing."
                messages.error(request, message)
                return redirect("staff_document_processing")
            locked_ticket.served_by = staff
            locked_ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
            locked_ticket.save(update_fields=["served_by", "claim_status", "updated_at"])
        messages.success(request, f"Started processing {ticket.queue_number}.")
    elif action == "ready" and ticket.claim_status == QueueTicket.ClaimStatus.PROCESSING:
        if ticket.served_by_id != staff.pk:
            messages.error(request, "This document is assigned to another staff member.")
            return redirect("staff_document_processing")
        ticket.claim_status = QueueTicket.ClaimStatus.READY
        ticket.save(update_fields=["claim_status", "updated_at"])
        notify_resident(
            appointment=ticket.appointment,
            notification_type=Notification.NotificationType.DOCUMENT_UPDATE,
            title="Document Ready for Claiming",
            message=f"Your {ticket.appointment.service.name} document is ready for claiming.",
            event_key=f"ticket:{ticket.pk}:document-ready",
        )
        messages.success(request, f"{ticket.queue_number} is ready for claiming.")
    else:
        messages.error(request, "That document action is not available.")
    return redirect("staff_document_processing")
