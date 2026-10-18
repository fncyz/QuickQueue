from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from qq.views import landing, signin, staff_logout
from qq.views.barangay_dashboard import barangay_dashboard
from qq.views.barangay_staff_portal import (
    staff_appointments, staff_review_appointment, staff_dashboard, staff_dashboard_mark_claimed,
    staff_document_action,
    staff_document_processing, staff_live_queue,
    staff_completed_documents, staff_document_preview,
    staff_resident_logbook,
    staff_settings,
    staff_document_notifications,
    staff_event_participant_history, staff_temporary_services, staff_temporary_service_form,
    staff_temporary_service_action, staff_event_scanner,
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
from qq.views.superadmin_dashboard import (
    superadmin_barangay_add,
    superadmin_barangay_detail,
    superadmin_barangay_edit,
    superadmin_barangay_status,
    superadmin_barangays,
    superadmin_dashboard,
    superadmin_placeholder,
)
from qq.views.superadmin_admins import (
    superadmin_admin_add, superadmin_admin_detail, superadmin_admin_edit,
    superadmin_admin_password_reset, superadmin_admin_status, superadmin_admins,
    superadmin_admin_temporary_password,
)
from qq.views.superadmin_verifications import (
    superadmin_verification_approve, superadmin_verification_detail,
    superadmin_verification_reject, superadmin_verifications,
)
from qq.views.superadmin_settings import superadmin_settings
from qq.views.mandatory_password import mandatory_password_change

urlpatterns = [
    path("", landing, name="index"),
    path("sign-in/", signin, name="signin"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="superadmin/password_reset_confirm.html",
        success_url=reverse_lazy("signin"),
    ), name="password_reset_confirm"),
    path("staff/logout/", staff_logout, name="staff_logout"),
    path("account/change-temporary-password/", mandatory_password_change, name="mandatory_password_change"),
    path("superadmin/dashboard/", superadmin_dashboard, name="superadmin_dashboard"),
    path("superadmin/barangays/", superadmin_barangays, name="superadmin_barangays"),
    path("superadmin/barangays/add/", superadmin_barangay_add, name="superadmin_barangay_add"),
    path("superadmin/barangays/<int:pk>/", superadmin_barangay_detail, name="superadmin_barangay_detail"),
    path("superadmin/barangays/<int:pk>/edit/", superadmin_barangay_edit, name="superadmin_barangay_edit"),
    path("superadmin/barangays/<int:pk>/status/", superadmin_barangay_status, name="superadmin_barangay_status"),
    path("superadmin/barangay-admins/", superadmin_admins, name="superadmin_barangay_admins"),
    path("superadmin/barangay-admins/add/", superadmin_admin_add, name="superadmin_admin_add"),
    path("superadmin/barangay-admins/<int:pk>/", superadmin_admin_detail, name="superadmin_admin_detail"),
    path("superadmin/barangay-admins/<int:pk>/edit/", superadmin_admin_edit, name="superadmin_admin_edit"),
    path("superadmin/barangay-admins/<int:pk>/status/", superadmin_admin_status, name="superadmin_admin_status"),
    path("superadmin/barangay-admins/<int:pk>/password-reset/", superadmin_admin_password_reset, name="superadmin_admin_password_reset"),
    path("superadmin/barangay-admins/<int:pk>/temporary-password/", superadmin_admin_temporary_password, name="superadmin_admin_temporary_password"),
    path("superadmin/pending-verifications/", superadmin_verifications, name="superadmin_pending_verifications"),
    path("superadmin/pending-verifications/<int:pk>/", superadmin_verification_detail, name="superadmin_verification_detail"),
    path("superadmin/pending-verifications/<int:pk>/approve/", superadmin_verification_approve, name="superadmin_verification_approve"),
    path("superadmin/pending-verifications/<int:pk>/reject/", superadmin_verification_reject, name="superadmin_verification_reject"),
    path("superadmin/system-settings/", superadmin_settings, name="superadmin_system_settings"),
    path("barangay/dashboard/", barangay_dashboard, name="barangay_dashboard"),
    path("barangay/staff/dashboard/", staff_dashboard, name="staff_dashboard"),
    path("barangay/staff/dashboard/documents/<int:pk>/claim/", staff_dashboard_mark_claimed, name="staff_dashboard_mark_claimed"),
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
    path("barangay/staff/events/", staff_temporary_services, name="staff_temporary_services"),
    path("barangay/staff/events/add/", staff_temporary_service_form, name="staff_temporary_service_add"),
    path("barangay/staff/events/<int:pk>/edit/", staff_temporary_service_form, name="staff_temporary_service_edit"),
    path("barangay/staff/events/<int:pk>/action/", staff_temporary_service_action, name="staff_temporary_service_action"),
    path("barangay/staff/events/<int:pk>/participants/", staff_event_participant_history, name="staff_event_participant_history"),
    path("barangay/staff/events/scanner/", staff_event_scanner, name="staff_event_scanner"),
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
]
