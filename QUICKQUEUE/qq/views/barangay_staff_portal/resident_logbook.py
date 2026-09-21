from collections import OrderedDict

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from qq.models import BarangayStaff, Notification, QueueTicket, Service


@login_required(login_url="signin")
def staff_resident_logbook(request):
    try:
        staff = request.user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This page is available to barangay staff accounts only.") from error
    if hasattr(request.user, "barangay_profile") or staff.role == BarangayStaff.Role.ADMIN:
        return redirect("barangay_residents")

    tickets = QueueTicket.objects.filter(
        appointment__barangay=staff.barangay,
        claim_status=QueueTicket.ClaimStatus.CLAIMED,
    ).select_related("appointment__resident", "appointment__service").order_by(
        "appointment__resident__last_name", "appointment__resident__first_name", "-claimed_at"
    )
    search = request.GET.get("q", "").strip()
    service = request.GET.get("service", "")
    date_filter = request.GET.get("date", "")
    if search:
        tickets = tickets.filter(
            Q(appointment__resident__first_name__icontains=search)
            | Q(appointment__resident__last_name__icontains=search)
            | Q(queue_number__icontains=search)
            | Q(appointment__service__name__icontains=search)
        )
    if service.isdigit():
        tickets = tickets.filter(appointment__service_id=int(service))
    if date_filter:
        try:
            tickets = tickets.filter(claimed_at__date=timezone.datetime.strptime(date_filter, "%Y-%m-%d").date())
        except ValueError:
            pass

    grouped = OrderedDict()
    for ticket in tickets:
        resident = ticket.appointment.resident
        if resident.pk not in grouped:
            grouped[resident.pk] = {"resident": resident, "latest": ticket, "transactions": []}
        grouped[resident.pk]["transactions"].append(ticket)

    return render(request, "barangay_staff/resident_logbook.html", {
        "active_page": "logbook", "staff": staff, "barangay": staff.barangay,
        "resident_rows": list(grouped.values()), "resident_count": len(grouped),
        "services": Service.objects.filter(is_active=True).order_by("name"),
        "filters": {"q": search, "service": service, "date": date_filter},
        "unread_notifications": Notification.objects.filter(
            appointment__barangay=staff.barangay, admin_is_read=False
        ).count(),
    })
