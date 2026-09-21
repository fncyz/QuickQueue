from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Barangay, BarangayStaff, Notification, QueueTicket


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        return user.staff_profile.barangay
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


def _parse_date(value, fallback):
    if not value:
        return fallback
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return fallback


def _ticket_base(barangay):
    return QueueTicket.objects.filter(appointment__barangay=barangay).select_related(
        "appointment__resident",
        "appointment__service",
        "appointment__time_slot",
    )


@login_required(login_url="signin")
def barangay_queue_history(request):
    """Queue history with claim workflow, completed list, and other appointments."""
    barangay = _barangay_for(request.user)
    today = timezone.localdate()
    default_start = today.replace(day=1)
    start_date = _parse_date(request.GET.get("start"), default_start)
    end_date = _parse_date(request.GET.get("end"), today)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    search = request.GET.get("q", "").strip()
    show_all_claims = request.GET.get("claims") == "all"
    try:
        per_page = int(request.GET.get("per_page", "10"))
    except ValueError:
        per_page = 10
    if per_page not in (5, 10, 20, 50):
        per_page = 10

    base = _ticket_base(barangay).filter(
        appointment__appointment_date__gte=start_date,
        appointment__appointment_date__lte=end_date,
    )

    to_be_claimed_qs = base.filter(
        status=QueueTicket.Status.COMPLETED,
        claim_status__in=[
            QueueTicket.ClaimStatus.PROCESSING,
            QueueTicket.ClaimStatus.READY,
        ],
    ).order_by("-completed_at", "queue_number")

    claimed_today = _ticket_base(barangay).filter(
        claim_status=QueueTicket.ClaimStatus.CLAIMED,
        claimed_at__date=today,
    ).count()

    processing_count = to_be_claimed_qs.filter(
        claim_status=QueueTicket.ClaimStatus.PROCESSING
    ).count()
    ready_count = to_be_claimed_qs.filter(
        claim_status=QueueTicket.ClaimStatus.READY
    ).count()

    claim_list = list(to_be_claimed_qs if show_all_claims else to_be_claimed_qs[:5])

    completed_qs = base.filter(status=QueueTicket.Status.COMPLETED).order_by(
        "-completed_at", "-appointment__appointment_date", "queue_number"
    )
    if search:
        completed_qs = completed_qs.filter(
            Q(queue_number__icontains=search)
            | Q(appointment__resident__first_name__icontains=search)
            | Q(appointment__resident__last_name__icontains=search)
            | Q(appointment__service__name__icontains=search)
        )

    paginator = Paginator(completed_qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    other_qs = base.filter(
        status__in=[QueueTicket.Status.CANCELLED, QueueTicket.Status.MISSED]
    ).order_by("-appointment__appointment_date", "queue_number")

    for ticket in list(claim_list) + list(page_obj) + list(other_qs[:10]):
        ticket.duration_label = ticket.processing_duration_label
        if ticket.status == QueueTicket.Status.MISSED and not ticket.notes:
            ticket.display_notes = "Resident did not show up"
        elif ticket.status == QueueTicket.Status.CANCELLED and not ticket.notes:
            ticket.display_notes = "Cancelled by resident"
        else:
            ticket.display_notes = ticket.notes or "—"

    return render(
        request,
        "barangay_admin/queue_history.html",
        {
            "active_page": "queue_history",
            "barangay": barangay,
            "today": today,
            "start_date": start_date,
            "end_date": end_date,
            "search": search,
            "show_all_claims": show_all_claims,
            "claim_tickets": claim_list,
            "claim_total": to_be_claimed_qs.count(),
            "processing_count": processing_count,
            "ready_count": ready_count,
            "claimed_today": claimed_today,
            "completed_page": page_obj,
            "completed_total": paginator.count,
            "per_page": per_page,
            "other_tickets": list(other_qs[:10]),
            "other_total": other_qs.count(),
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )


def _redirect_history():
    return redirect(f"{reverse('barangay_queue_history')}#to-be-claimed")


@login_required(login_url="signin")
@require_POST
def barangay_mark_claim_ready(request, pk):
    """Mark a processing document as ready for claiming."""
    barangay = _barangay_for(request.user)
    ticket = get_object_or_404(
        QueueTicket.objects.select_related("appointment"),
        pk=pk,
        appointment__barangay=barangay,
        status=QueueTicket.Status.COMPLETED,
    )
    if ticket.claim_status != QueueTicket.ClaimStatus.PROCESSING:
        messages.error(request, "Only processing documents can be marked ready.")
        return _redirect_history()

    ticket.claim_status = QueueTicket.ClaimStatus.READY
    ticket.save(update_fields=["claim_status", "updated_at"])

    Notification.objects.create(
        resident=ticket.appointment.resident,
        appointment=ticket.appointment,
        notification_type=Notification.NotificationType.QUEUE_UPDATE,
        title="Document Ready for Claiming",
        message=(
            f"Your document for queue number {ticket.queue_number} "
            "is ready for claiming at the barangay office."
        ),
    )
    messages.success(request, f"{ticket.queue_number} is ready for claiming.")
    return _redirect_history()


@login_required(login_url="signin")
@require_POST
def barangay_mark_claimed(request, pk):
    """Mark a ready document as claimed by the resident."""
    barangay = _barangay_for(request.user)
    ticket = get_object_or_404(
        QueueTicket.objects.select_related("appointment"),
        pk=pk,
        appointment__barangay=barangay,
        status=QueueTicket.Status.COMPLETED,
    )
    if ticket.claim_status != QueueTicket.ClaimStatus.READY:
        messages.error(request, "Only ready documents can be marked as claimed.")
        return _redirect_history()

    ticket.claim_status = QueueTicket.ClaimStatus.CLAIMED
    ticket.claimed_at = timezone.now()
    ticket.save(update_fields=["claim_status", "claimed_at", "updated_at"])

    Notification.objects.create(
        resident=ticket.appointment.resident,
        appointment=ticket.appointment,
        notification_type=Notification.NotificationType.QUEUE_UPDATE,
        title="Document Claimed",
        message=f"Queue number {ticket.queue_number} has been marked as claimed.",
    )
    messages.success(request, f"{ticket.queue_number} marked as claimed.")
    return _redirect_history()
