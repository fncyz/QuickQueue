from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from qq.models import Barangay, Notification, QueueTicket, Service


SERVICE_ICONS = {
    "BC": "clearance",
    "COR": "residency",
    "COI": "indigency",
    "BPA": "business",
    "FC": "complaint",
}


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


def _avg_processing_minutes(barangay, day):
    tickets = (
        QueueTicket.objects.filter(
            appointment__barangay=barangay,
            status=QueueTicket.Status.COMPLETED,
            completed_at__date=day,
            called_at__isnull=False,
            completed_at__isnull=False,
        )
        .only("called_at", "completed_at")
    )
    durations = []
    for ticket in tickets:
        seconds = (ticket.completed_at - ticket.called_at).total_seconds()
        if seconds > 0:
            durations.append(seconds / 60)
    if not durations:
        return None
    return round(sum(durations) / len(durations), 1)


@login_required(login_url="signin")
def barangay_waiting_time(request):
    """AI waiting-time settings: configure per-service estimated durations."""
    barangay = _barangay_for(request.user)
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    services = list(Service.objects.filter(is_active=True).order_by("name"))
    for service in services:
        service.icon_key = SERVICE_ICONS.get(service.code, "default")

    avg_today = _avg_processing_minutes(barangay, today)
    avg_yesterday = _avg_processing_minutes(barangay, yesterday)

    if avg_today is None:
        configured_avg = Service.objects.filter(is_active=True).aggregate(
            avg=Avg("estimated_duration")
        )["avg"]
        avg_today = round(float(configured_avg), 1) if configured_avg else 0.0
        using_fallback = True
    else:
        using_fallback = False

    comparison = None
    if avg_yesterday is not None:
        diff = round(avg_yesterday - avg_today, 1)
        if diff > 0:
            comparison = {
                "label": f"{diff} mins faster",
                "direction": "faster",
                "yesterday": avg_yesterday,
            }
        elif diff < 0:
            comparison = {
                "label": f"{abs(diff)} mins slower",
                "direction": "slower",
                "yesterday": avg_yesterday,
            }
        else:
            comparison = {
                "label": "Same as yesterday",
                "direction": "same",
                "yesterday": avg_yesterday,
            }

    return render(
        request,
        "barangay_admin/waiting_time.html",
        {
            "active_page": "waiting",
            "barangay": barangay,
            "today": today,
            "services": services,
            "avg_today": avg_today,
            "using_fallback": using_fallback,
            "comparison": comparison,
            "unread_notifications": Notification.objects.filter(
                appointment__barangay=barangay,
                admin_is_read=False,
            ).count(),
        },
    )


@login_required(login_url="signin")
@require_POST
def barangay_waiting_time_update(request, pk):
    """Update one service estimated duration from the AI Waiting Time page."""
    _barangay_for(request.user)
    service = get_object_or_404(Service, pk=pk, is_active=True)

    raw = request.POST.get("estimated_duration", "").strip()
    try:
        minutes = int(raw)
    except ValueError:
        messages.error(request, "Enter a valid number of minutes.")
        return redirect("barangay_waiting_time")

    if minutes < 1:
        messages.error(request, "Estimated time must be at least 1 minute.")
        return redirect("barangay_waiting_time")

    if service.estimated_duration != minutes:
        service.estimated_duration = minutes
        service.save(update_fields=["estimated_duration", "updated_at"])
        messages.success(
            request,
            f"Updated {service.name} to {minutes} minute{'s' if minutes != 1 else ''}.",
        )
    else:
        messages.info(request, f"{service.name} is already set to {minutes} mins.")

    return redirect("barangay_waiting_time")
