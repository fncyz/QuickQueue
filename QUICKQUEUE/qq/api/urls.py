from django.urls import path

from .views import (
    login_api,
    profile_api,
    change_password_api,
    set_initial_password_api,
    register_api,
    barangay_list_api,
    appointments_api,
    queue_status_api,
    transactions_api,
    document_templates_api,
    document_template_detail_api,
    notifications_api,
)

urlpatterns = [
    path("login/", login_api, name="api_login"),
    path("register/", register_api, name="api_register"),
    path("profile/", profile_api, name="api_profile"),
    path("change-password/", change_password_api, name="api_change_password"),
    path("set-initial-password/", set_initial_password_api, name="api_set_initial_password"),
    path("barangays/",barangay_list_api,name="barangay_list"),
    path("appointments/", appointments_api, name="api_appointments"),
    path("queue-status/", queue_status_api, name="api_queue_status"),
    path("transactions/", transactions_api, name="api_transactions"),
    path("notifications/", notifications_api, name="api_notifications"),
    path("document-templates/", document_templates_api, name="api_document_templates"),
    path("document-templates/<int:pk>/", document_template_detail_api, name="api_document_template_detail"),
]
