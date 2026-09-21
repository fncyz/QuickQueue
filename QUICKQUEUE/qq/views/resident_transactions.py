from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from qq.models import Appointment


@login_required(login_url="signin")
def resident_transactions(request):
    """Display the signed-in resident's appointment history."""
    appointments = request.user.resident_profile.appointments.select_related(
        "service"
    ).order_by("-appointment_date", "-created_at")
    return render(
        request,
        "resident/transactions.html",
        {"appointments": appointments, "active_page": "transactions"},
    )


@login_required(login_url="signin")
@require_POST
def resident_delete_appointment(request, pk):
    """Delete a completed, cancelled, or missed appointment owned by the resident."""
    resident = request.user.resident_profile
    deletable_statuses = (
        Appointment.Status.COMPLETED,
        Appointment.Status.CANCELLED,
        Appointment.Status.MISSED,
    )

    with transaction.atomic():
        appointment = get_object_or_404(
            Appointment.objects.select_for_update(),
            pk=pk,
            resident=resident,
        )
        if appointment.status not in deletable_statuses:
            messages.error(request, "Only past or cancelled appointments can be deleted.")
            return redirect("resident_transactions")

        appointment.delete()

    messages.success(request, "Appointment deleted from your history.")
    return redirect("resident_transactions")
