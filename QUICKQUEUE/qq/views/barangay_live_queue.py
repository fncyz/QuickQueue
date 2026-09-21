from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, ExpressionWrapper, F, DurationField
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Appointment, Barangay, BarangayStaff, Notification, QueueTicket, Service, TimeSlot


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        return user.staff_profile.barangay
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


def _window_label(slots, slot):
    slots = list(slots)
    try:
        index = slots.index(slot)
    except ValueError:
        index = 0
    return chr(65 + (index % 26))


def _resolve_slot(barangay, slot_id, today, now_time):
    slots = list(
        TimeSlot.objects.filter(barangay=barangay, is_active=True).order_by("start_time")
    )
    if not slots:
        return None, []

    if slot_id and str(slot_id).isdigit():
        selected = next((slot for slot in slots if slot.id == int(slot_id)), None)
        if selected:
            return selected, slots

    for slot in slots:
        if slot.start_time <= now_time <= slot.end_time:
            return slot, slots

    busy = (
        QueueTicket.objects.filter(
            appointment__barangay=barangay,
            appointment__appointment_date=today,
            appointment__time_slot__in=slots,
            status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.NOW_SERVING],
        )
        .values_list("appointment__time_slot_id", flat=True)
        .first()
    )
    if busy:
        selected = next((slot for slot in slots if slot.id == busy), slots[0])
        return selected, slots

    return slots[0], slots


def _annotate_wait_estimates(tickets):
    """Attach AI wait estimates using each service's estimated duration."""
    cumulative = 0
    previous_number = None
    serving = next(
        (ticket for ticket in tickets if ticket.status == QueueTicket.Status.NOW_SERVING),
        None,
    )
    if serving:
        cumulative = serving.appointment.service.estimated_duration
        previous_number = serving.queue_number

    for ticket in tickets:
        duration = ticket.appointment.service.estimated_duration
        if ticket.status == QueueTicket.Status.COMPLETED:
            ticket.wait_label = "—"
            ticket.wait_minutes = None
        elif ticket.status == QueueTicket.Status.NOW_SERVING:
            ticket.wait_label = "Serving"
            ticket.wait_minutes = 0
        elif ticket.status == QueueTicket.Status.WAITING:
            ticket.wait_minutes = cumulative
            if previous_number:
                ticket.wait_label = f"~{ticket.wait_minutes} mins (After {previous_number})"
            else:
                ticket.wait_label = f"~{ticket.wait_minutes} mins"
            cumulative += duration
            previous_number = ticket.queue_number
        else:
            ticket.wait_label = "—"
            ticket.wait_minutes = None
    return tickets


def _ticket_queryset(barangay, today, slot):
    return (
        QueueTicket.objects.filter(
            appointment__barangay=barangay,
            appointment__appointment_date=today,
            appointment__time_slot=slot,
        )
        .exclude(status=QueueTicket.Status.CANCELLED)
        .select_related(
            "appointment__resident",
            "appointment__service",
            "appointment__time_slot",
        )
        .order_by("queue_number")
    )


def _redirect_live_queue(slot_id=None):
    url = reverse("barangay_live_queue")
    if slot_id:
        return redirect(f"{url}?slot={slot_id}")
    return redirect(url)


@login_required(login_url="signin")
def barangay_live_queue(request):
    """Live queue board for the signed-in barangay staff account."""
    if (
        hasattr(request.user, "staff_profile")
        and not hasattr(request.user, "barangay_profile")
        and request.user.staff_profile.role != BarangayStaff.Role.ADMIN
    ):
        return redirect("staff_live_queue")
    barangay = _barangay_for(request.user)
    today = timezone.localdate()
    now = timezone.localtime()
    current_slot, slots = _resolve_slot(
        barangay, request.GET.get("slot"), today, now.time()
    )

    tickets = []
    now_serving = None
    waiting_count = 0
    completed_count = 0
    serving_count = 0
    next_in_line = []
    next_wait_minutes = None
    window = "A"

    if current_slot:
        window = _window_label(slots, current_slot)
        tickets = _annotate_wait_estimates(list(_ticket_queryset(barangay, today, current_slot)))
        now_serving = next(
            (ticket for ticket in tickets if ticket.status == QueueTicket.Status.NOW_SERVING),
            None,
        )
        waiting_count = sum(1 for ticket in tickets if ticket.status == QueueTicket.Status.WAITING)
        completed_count = sum(
            1 for ticket in tickets if ticket.status == QueueTicket.Status.COMPLETED
        )
        serving_count = sum(
            1 for ticket in tickets if ticket.status == QueueTicket.Status.NOW_SERVING
        )
        next_in_line = [
            ticket for ticket in tickets if ticket.status == QueueTicket.Status.WAITING
        ][:3]
        if next_in_line:
            next_wait_minutes = next_in_line[0].wait_minutes

    today_tickets = QueueTicket.objects.filter(
        appointment__barangay=barangay,
        appointment__appointment_date=today,
    ).exclude(status=QueueTicket.Status.CANCELLED)

    completed_today = today_tickets.filter(status=QueueTicket.Status.COMPLETED)
    avg_seconds = (
        completed_today.exclude(called_at=None)
        .exclude(completed_at=None)
        .annotate(
            service_seconds=ExpressionWrapper(
                F("completed_at") - F("called_at"),
                output_field=DurationField(),
            )
        )
        .aggregate(avg=Avg("service_seconds"))["avg"]
    )
    if avg_seconds:
        average_service_minutes = round(avg_seconds.total_seconds() / 60, 1)
    else:
        service_avg = Service.objects.filter(is_active=True).aggregate(
            avg=Avg("estimated_duration")
        )["avg"]
        average_service_minutes = round(service_avg, 1) if service_avg else 0

    current_index = slots.index(current_slot) if current_slot in slots else -1
    next_slot = slots[current_index + 1] if 0 <= current_index < len(slots) - 1 else None

    return render(
        request,
        "barangay_admin/live_queue.html",
        {
            "active_page": "queue",
            "barangay": barangay,
            "today": today,
            "current_slot": current_slot,
            "slots": slots,
            "window_label": window,
            "tickets": tickets,
            "now_serving": now_serving,
            "waiting_count": waiting_count,
            "completed_count": completed_count,
            "serving_count": serving_count,
            "slot_capacity": current_slot.max_appointments if current_slot else 0,
            "next_in_line": next_in_line,
            "next_wait_minutes": next_wait_minutes,
            "next_slot": next_slot,
            "services": Service.objects.filter(is_active=True).order_by("name"),
            "stats": {
                "average_service_minutes": average_service_minutes,
                "completed_today": completed_today.count(),
                "waiting_today": today_tickets.filter(
                    status=QueueTicket.Status.WAITING
                ).count(),
                "total_today": today_tickets.count(),
            },
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )


@login_required(login_url="signin")
@require_POST
def barangay_queue_call_next(request):
    """Move the first waiting ticket to Now Serving."""
    barangay = _barangay_for(request.user)
    today = timezone.localdate()
    slot_id = request.POST.get("slot")
    current_slot, _slots = _resolve_slot(
        barangay, slot_id, today, timezone.localtime().time()
    )
    if not current_slot:
        messages.error(request, "No active time slot is available.")
        return _redirect_live_queue()

    with transaction.atomic():
        serving = (
            QueueTicket.objects.select_for_update()
            .filter(
                appointment__barangay=barangay,
                appointment__appointment_date=today,
                appointment__time_slot=current_slot,
                status=QueueTicket.Status.NOW_SERVING,
            )
            .first()
        )
        if serving:
            messages.error(
                request,
                f"{serving.queue_number} is still being served. Complete or skip first.",
            )
            return _redirect_live_queue(current_slot.id)

        nxt = (
            QueueTicket.objects.select_for_update()
            .filter(
                appointment__barangay=barangay,
                appointment__appointment_date=today,
                appointment__time_slot=current_slot,
                status=QueueTicket.Status.WAITING,
            )
            .order_by("queue_number")
            .first()
        )
        if not nxt:
            messages.info(request, "No residents are waiting in this time slot.")
            return _redirect_live_queue(current_slot.id)

        now = timezone.now()
        nxt.status = QueueTicket.Status.NOW_SERVING
        nxt.called_at = now
        nxt.save(update_fields=["status", "called_at", "updated_at"])
        nxt.appointment.status = Appointment.Status.ONGOING
        nxt.appointment.save(update_fields=["status", "updated_at"])

        Notification.objects.create(
            resident=nxt.appointment.resident,
            appointment=nxt.appointment,
            notification_type=Notification.NotificationType.QUEUE_UPDATE,
            title="Now Serving",
            message=f"Your queue number {nxt.queue_number} is now being served.",
        )

    messages.success(
        request, f"Now serving {nxt.queue_number} · {nxt.appointment.resident}."
    )
    return _redirect_live_queue(current_slot.id)


@login_required(login_url="signin")
@require_POST
def barangay_queue_complete(request, pk):
    """Mark a now-serving ticket as completed."""
    barangay = _barangay_for(request.user)
    ticket = get_object_or_404(
        QueueTicket.objects.select_related(
            "appointment__resident", "appointment__time_slot"
        ),
        pk=pk,
        appointment__barangay=barangay,
    )
    if ticket.status != QueueTicket.Status.NOW_SERVING:
        messages.error(request, "Only a now-serving ticket can be completed.")
        return _redirect_live_queue(ticket.appointment.time_slot_id)

    now = timezone.now()
    ticket.status = QueueTicket.Status.COMPLETED
    ticket.completed_at = now
    ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
    if not ticket.requirements:
        ticket.requirements = "Valid ID"
    ticket.save(update_fields=["status", "completed_at", "claim_status", "requirements", "updated_at"])
    ticket.appointment.status = Appointment.Status.COMPLETED
    ticket.appointment.save(update_fields=["status", "updated_at"])

    Notification.objects.create(
        resident=ticket.appointment.resident,
        appointment=ticket.appointment,
        notification_type=Notification.NotificationType.APPOINTMENT_COMPLETED,
        title="Service Completed",
        message=f"Your queue number {ticket.queue_number} has been completed.",
    )

    messages.success(request, f"Completed {ticket.queue_number}.")
    return _redirect_live_queue(ticket.appointment.time_slot_id)


@login_required(login_url="signin")
@require_POST
def barangay_queue_skip(request):
    """Skip the currently serving ticket and mark it as missed."""
    barangay = _barangay_for(request.user)
    today = timezone.localdate()
    slot_id = request.POST.get("slot")
    current_slot, _slots = _resolve_slot(
        barangay, slot_id, today, timezone.localtime().time()
    )
    if not current_slot:
        messages.error(request, "No active time slot is available.")
        return _redirect_live_queue()

    serving = (
        QueueTicket.objects.filter(
            appointment__barangay=barangay,
            appointment__appointment_date=today,
            appointment__time_slot=current_slot,
            status=QueueTicket.Status.NOW_SERVING,
        )
        .select_related("appointment__resident")
        .first()
    )

    if not serving:
        messages.info(request, "No resident is currently being served.")
        return _redirect_live_queue(current_slot.id)

    serving.status = QueueTicket.Status.MISSED
    serving.notes = serving.notes or "Resident did not show up"
    serving.save(update_fields=["status", "notes", "updated_at"])
    serving.appointment.status = Appointment.Status.MISSED
    serving.appointment.save(update_fields=["status", "updated_at"])

    Notification.objects.create(
        resident=serving.appointment.resident,
        appointment=serving.appointment,
        notification_type=Notification.NotificationType.QUEUE_UPDATE,
        title="Queue Skipped",
        message=(
            f"Your queue number {serving.queue_number} was skipped. "
            "Please check with barangay staff."
        ),
    )

    messages.warning(request, f"Skipped {serving.queue_number}.")
    return _redirect_live_queue(current_slot.id)


@login_required(login_url="signin")
@require_POST
def barangay_update_service_times(request):
    """Update default estimated service durations used by AI waiting estimates."""
    _barangay_for(request.user)
    updated = 0
    for service in Service.objects.filter(is_active=True):
        raw = request.POST.get(f"service_{service.pk}", "").strip()
        if not raw:
            continue
        try:
            minutes = int(raw)
        except ValueError:
            continue
        if minutes < 1:
            continue
        if service.estimated_duration != minutes:
            service.estimated_duration = minutes
            service.save(update_fields=["estimated_duration", "updated_at"])
            updated += 1

    if updated:
        messages.success(request, f"Updated {updated} service time setting(s).")
    else:
        messages.info(request, "No service times were changed.")

    return _redirect_live_queue(request.POST.get("slot"))
