from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import redirect, render

from qq.models import Service, TimeSlot
from qq.services.appointment_service import create_appointment
from qq.services.timeslot_service import ensure_default_time_slots


@login_required(login_url="signin")
def resident_booking(request):
    """Show the appointment-booking form for the signed-in resident."""
    if not hasattr(request.user, "resident_profile"):
        messages.error(request, "The Book Now page is available to resident accounts only.")
        if hasattr(request.user, "barangay_profile"):
            return redirect("barangay_dashboard")
        if hasattr(request.user, "staff_profile"):
            return redirect("staff_dashboard")
        return redirect("index")

    resident = request.user.resident_profile
    services = Service.objects.filter(is_active=True).order_by("name")
    ensure_default_time_slots(resident.barangay)
    time_slots = TimeSlot.objects.filter(
        barangay=resident.barangay,
        is_active=True,
    ).order_by("start_time")
    if request.method == "POST":
        try:
            service = services.get(pk=request.POST.get("service"))
            time_slot = time_slots.get(pk=request.POST.get("time_slot"))
            appointment_date = date.fromisoformat(request.POST.get("appointment_date", ""))
            sitio = request.POST.get("sitio", "").strip()
            if appointment_date < date.today():
                raise ValueError("Please choose today or a future appointment date.")
            if not sitio:
                raise ValueError("Please enter your sitio or purok.")
            if len(sitio) > 100:
                raise ValueError("Sitio or purok must not exceed 100 characters.")
            create_appointment(
                resident, service, appointment_date, time_slot,
                request.POST.get("purpose", "").strip(),
                sitio,
            )
            messages.success(request, "Appointment booked. Your queue number is ready.")
            return redirect("resident_queue_status")
        except (Service.DoesNotExist, TimeSlot.DoesNotExist):
            messages.error(request, "Please select a valid service, date, and time slot.")
        except ValueError as error:
            messages.error(request, str(error))
        except IntegrityError:
            messages.error(
                request,
                "That queue position was just taken. Please submit your booking again.",
            )

    return render(
        request,
        "resident/booking.html",
        {
            "resident": resident,
            "services": services,
            "time_slots": time_slots,
            "active_page": "booking",
        },
    )
