from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.formats import date_format, time_format
from django.views.decorators.http import require_GET

from qq.models import Appointment, Barangay, BarangayStaff, QueueTicket, Resident


def _admin_barangay(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error
    if staff.role != BarangayStaff.Role.ADMIN:
        raise PermissionDenied("Barangay administrator access is required.")
    return staff.barangay


def _value(value):
    return str(value) if value not in (None, "") else "—"


def _date(value, include_time=False):
    if not value:
        return "—"
    if include_time:
        value = timezone.localtime(value)
        return date_format(value, "M j, Y g:i A")
    return date_format(value, "M j, Y")


def _slot_label(slot):
    if not slot:
        return "—"
    return f'{time_format(slot.start_time, "g:i A")} – {time_format(slot.end_time, "g:i A")}'


def _appointment_details(barangay, pk):
    appointment = get_object_or_404(
        Appointment.objects.filter(barangay=barangay).select_related(
            "resident", "service", "time_slot", "event_booking"
        ),
        pk=pk,
    )
    booking = getattr(appointment, "event_booking", None)
    is_special_service = appointment.service.is_temporary
    status_label = booking.get_status_display() if booking else appointment.get_status_display()
    appointment_fields = [
        {"label": "Resident", "value": str(appointment.resident)},
        {"label": "Service", "value": appointment.service.name},
        {"label": "Appointment Date", "value": _date(appointment.appointment_date)},
    ]
    if is_special_service:
        appointment_fields.append(
            {
                "label": "Booking Reference",
                "value": booking.booking_reference if booking else "Not available",
            }
        )
    else:
        appointment_fields.extend(
            [
                {"label": "Time Slot", "value": _slot_label(appointment.time_slot)},
                {"label": "Queue Number", "value": _value(appointment.queue_number)},
            ]
        )
    appointment_fields.append({"label": "Status", "value": status_label})

    request_fields = []
    if not is_special_service:
        request_fields.extend(
            [
                {"label": "Purpose", "value": _value(appointment.purpose)},
                {"label": "Sitio / Purok", "value": _value(appointment.sitio)},
            ]
        )
    request_fields.extend(
        [
            {"label": "Booked On", "value": _date(appointment.created_at, True)},
            {
                "label": "Booking Type",
                "value": "Special Service" if is_special_service else "Regular Service",
            },
        ]
    )
    return {
        "title": "Appointment Details",
        "subtitle": appointment.queue_number or appointment.service.name,
        "sections": [
            {
                "heading": "Appointment Information",
                "fields": appointment_fields,
            },
            {
                "heading": "Request Details",
                "fields": request_fields,
            },
        ],
    }


def _resident_details(barangay, pk):
    resident = get_object_or_404(
        Resident.objects.filter(barangay=barangay).select_related("user"), pk=pk
    )
    full_address = ", ".join(
        part for part in (resident.barangay.name, resident.municipality, resident.province) if part
    )
    return {
        "title": "Resident Details",
        "subtitle": str(resident),
        "sections": [
            {
                "heading": "Personal Information",
                "fields": [
                    {"label": "Full Name", "value": str(resident)},
                    {"label": "Sex", "value": resident.get_sex_display()},
                    {"label": "Birthdate", "value": _date(resident.birthdate)},
                    {"label": "Age", "value": str(resident.age)},
                    {"label": "Barangay / Location", "value": full_address},
                ],
            },
            {
                "heading": "Account Information",
                "fields": [
                    {"label": "Contact Number", "value": resident.contact_number},
                    {"label": "Email", "value": _value(resident.email)},
                    {"label": "Account Status", "value": "Active" if resident.user.is_active else "Inactive"},
                    {"label": "Registered On", "value": _date(resident.created_at, True)},
                ],
            },
        ],
    }


def _queue_details(barangay, pk):
    ticket = get_object_or_404(
        QueueTicket.objects.filter(appointment__barangay=barangay).select_related(
            "appointment__resident",
            "appointment__service",
            "appointment__time_slot",
            "service_window",
            "served_by",
        ),
        pk=pk,
    )
    appointment = ticket.appointment
    return {
        "title": "Queue Transaction Details",
        "subtitle": ticket.queue_number,
        "sections": [
            {
                "heading": "Queue Information",
                "fields": [
                    {"label": "Queue Number", "value": ticket.queue_number},
                    {"label": "Resident", "value": str(appointment.resident)},
                    {"label": "Service", "value": appointment.service.name},
                    {"label": "Appointment Date", "value": _date(appointment.appointment_date)},
                    {"label": "Time Slot", "value": _slot_label(appointment.time_slot)},
                    {"label": "Queue Status", "value": ticket.get_status_display()},
                ],
            },
            {
                "heading": "Service Details",
                "fields": [
                    {"label": "Assigned Window", "value": ticket.service_window.name if ticket.service_window else "Unassigned"},
                    {"label": "Processed By", "value": ticket.served_by.full_name if ticket.served_by else "—"},
                    {"label": "Called At", "value": _date(ticket.called_at, True)},
                    {"label": "Completed At", "value": _date(ticket.completed_at, True)},
                    {"label": "Processing Duration", "value": ticket.processing_duration_label},
                    {"label": "Document Status", "value": ticket.get_claim_status_display()},
                    {"label": "Notes", "value": _value(ticket.notes)},
                ],
            },
        ],
    }


DETAIL_LOADERS = {
    "appointment": _appointment_details,
    "resident": _resident_details,
    "queue-ticket": _queue_details,
}


@login_required(login_url="signin")
@require_GET
def barangay_admin_record_detail(request, record_type, pk):
    barangay = _admin_barangay(request.user)
    loader = DETAIL_LOADERS.get(record_type)
    if not loader:
        raise Http404("Unknown record type.")
    return JsonResponse(loader(barangay, pk))
