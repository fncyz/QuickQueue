from django.urls import path

from qq.views import index, signin, signup, barangay_admin_registration
from qq.views.resident_home import resident_home
from qq.views.resident_home import resident_logout
from qq.views.resident_booking import resident_booking
from qq.views.resident_profile import resident_profile
from qq.views.resident_transactions import resident_delete_appointment, resident_transactions
from qq.views.resident_queue import resident_cancel_appointment, resident_check_in, resident_queue_status
from qq.views.resident_about import resident_about
from qq.views.barangay_dashboard import barangay_dashboard
from qq.views.barangay_staff_portal import (
    staff_appointments, staff_review_appointment, staff_dashboard, staff_document_action,
    staff_document_processing, staff_live_queue,
    staff_completed_documents, staff_document_preview,
    staff_resident_logbook,
    staff_settings,
    staff_document_notifications,
)
from qq.views.barangay_appointments import (
    barangay_appointments,
    barangay_confirm_appointment,
)
from qq.views.barangay_live_queue import (
    barangay_live_queue,
    barangay_queue_call_next,
    barangay_queue_complete,
    barangay_queue_skip,
    barangay_update_service_times,
)
from qq.views.barangay_queue_history import (
    barangay_queue_history,
    barangay_mark_claim_ready,
    barangay_mark_claimed,
)
from qq.views.barangay_residents import barangay_residents
from qq.views.barangay_staff import (
    barangay_staff,
    barangay_staff_add,
    barangay_staff_edit,
)
from qq.views.barangay_waiting_time import (
    barangay_waiting_time,
    barangay_waiting_time_update,
)
from qq.views.barangay_settings import barangay_settings
from qq.views.barangay_notifications import barangay_notifications
from qq.views.barangay_document_templates import barangay_document_templates

urlpatterns = [
    path("", index, name="index"),
    path("sign-in/", signin, name="signin"),
    path("create-account/", signup, name="signup"),
    path("barangay-admin-registration/", barangay_admin_registration, name="barangay_admin_registration"),
    path("barangay/dashboard/", barangay_dashboard, name="barangay_dashboard"),
    path("barangay/staff/dashboard/", staff_dashboard, name="staff_dashboard"),
    path("barangay/staff/appointments/", staff_appointments, name="staff_appointments"),
    path("barangay/staff/appointments/<int:pk>/review/", staff_review_appointment, name="staff_review_appointment"),
    path("barangay/staff/queue/live/", staff_live_queue, name="staff_live_queue"),
    # Dedicated staff document workflow and archive.
    path("barangay/staff/documents/", staff_document_processing, name="staff_document_processing"),
    path("barangay/staff/documents/<int:pk>/action/", staff_document_action, name="staff_document_action"),
    path("barangay/staff/documents/<int:pk>/preview/", staff_document_preview, name="staff_processing_document_preview"),
    path("barangay/staff/documents/completed/", staff_completed_documents, name="staff_completed_documents"),
    path("barangay/staff/documents/completed/<int:pk>/", staff_document_preview, name="staff_document_preview"),
    path("barangay/staff/residents/", staff_resident_logbook, name="staff_resident_logbook"),
    path("barangay/staff/settings/", staff_settings, name="staff_settings"),
    path("barangay/staff/notifications/documents/", staff_document_notifications, name="staff_document_notifications"),
    path("barangay/appointments/", barangay_appointments, name="barangay_appointments"),
    path(
        "barangay/appointments/<int:pk>/confirm/",
        barangay_confirm_appointment,
        name="barangay_confirm_appointment",
    ),
    path("barangay/queue/live/", barangay_live_queue, name="barangay_live_queue"),
    path("barangay/queue/history/", barangay_queue_history, name="barangay_queue_history"),
    path("barangay/residents/", barangay_residents, name="barangay_residents"),
    path("barangay/staff/", barangay_staff, name="barangay_staff"),
    path("barangay/staff/add/", barangay_staff_add, name="barangay_staff_add"),
    path("barangay/staff/<int:pk>/edit/", barangay_staff_edit, name="barangay_staff_edit"),
    path("barangay/settings/", barangay_settings, name="barangay_settings"),
    path("barangay/document-templates/", barangay_document_templates, name="barangay_document_templates"),
    path("barangay/notifications/", barangay_notifications, name="barangay_notifications"),
    path("barangay/waiting-time/", barangay_waiting_time, name="barangay_waiting_time"),
    path(
        "barangay/waiting-time/<int:pk>/update/",
        barangay_waiting_time_update,
        name="barangay_waiting_time_update",
    ),
    path(
        "barangay/queue/<int:pk>/mark-ready/",
        barangay_mark_claim_ready,
        name="barangay_mark_claim_ready",
    ),
    path(
        "barangay/queue/<int:pk>/mark-claimed/",
        barangay_mark_claimed,
        name="barangay_mark_claimed",
    ),
    path("barangay/queue/call-next/", barangay_queue_call_next, name="barangay_queue_call_next"),
    path("barangay/queue/<int:pk>/complete/", barangay_queue_complete, name="barangay_queue_complete"),
    path("barangay/queue/skip/", barangay_queue_skip, name="barangay_queue_skip"),
    path(
        "barangay/queue/service-times/",
        barangay_update_service_times,
        name="barangay_update_service_times",
    ),
    path("resident/home/", resident_home, name="resident_home"),
    path("resident/book-now/", resident_booking, name="resident_booking"),
    path("resident/queue-status/", resident_queue_status, name="resident_queue_status"),
    path(
        "resident/appointments/<int:pk>/check-in/",
        resident_check_in,
        name="resident_check_in",
    ),
    path(
        "resident/appointments/<int:pk>/cancel/",
        resident_cancel_appointment,
        name="resident_cancel_appointment",
    ),
    path("resident/profile/", resident_profile, name="resident_profile"),
    path("resident/transactions/", resident_transactions, name="resident_transactions"),
    path(
        "resident/appointments/<int:pk>/delete/",
        resident_delete_appointment,
        name="resident_delete_appointment",
    ),
    path("resident/about/", resident_about, name="resident_about"),
    path("logout/", resident_logout, name="resident_logout"),
]
