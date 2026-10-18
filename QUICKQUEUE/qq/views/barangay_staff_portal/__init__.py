from .dashboard import staff_dashboard, staff_dashboard_mark_claimed
from .temporary_services import (
    staff_event_participant_history, staff_event_scanner, staff_temporary_service_action,
    staff_temporary_service_form, staff_temporary_services,
)
from .appointments import staff_appointments, staff_review_appointment
from .live_queue import staff_live_queue
from .documents import staff_document_action, staff_document_processing
from .completed_documents import staff_completed_documents, staff_document_preview
from .resident_logbook import staff_resident_logbook
from .settings import staff_settings
from .notifications import staff_document_notifications

__all__ = [
    "staff_dashboard", "staff_dashboard_mark_claimed", "staff_appointments", "staff_review_appointment", "staff_live_queue",
    "staff_document_processing", "staff_document_action",
    "staff_completed_documents", "staff_document_preview",
    "staff_resident_logbook",
    "staff_settings",
    "staff_document_notifications",
    "staff_temporary_services", "staff_temporary_service_form", "staff_temporary_service_action",
    "staff_event_scanner", "staff_event_participant_history",
]
