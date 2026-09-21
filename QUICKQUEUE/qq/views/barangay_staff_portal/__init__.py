from .dashboard import staff_dashboard
from .appointments import staff_appointments, staff_review_appointment
from .live_queue import staff_live_queue
from .documents import staff_document_action, staff_document_processing
from .completed_documents import staff_completed_documents, staff_document_preview
from .resident_logbook import staff_resident_logbook
from .settings import staff_settings
from .notifications import staff_document_notifications

__all__ = [
    "staff_dashboard", "staff_appointments", "staff_review_appointment", "staff_live_queue",
    "staff_document_processing", "staff_document_action",
    "staff_completed_documents", "staff_document_preview",
    "staff_resident_logbook",
    "staff_settings",
    "staff_document_notifications",
]
