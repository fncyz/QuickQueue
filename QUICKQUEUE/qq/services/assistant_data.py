from dataclasses import dataclass, field
from decimal import Decimal
import re

from django.conf import settings
from django.db.models import F, Prefetch, Q
from django.utils import timezone

from qq.models import (
    Appointment,
    AssistantKnowledge,
    BarangayServiceConfiguration,
    EventBooking,
    QueueTicket,
    Service,
)


ACTIVE_APPOINTMENT_STATUSES = (
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
    Appointment.Status.ONGOING,
)
ACTIVE_QUEUE_STATUSES = (QueueTicket.Status.WAITING, QueueTicket.Status.NOW_SERVING)


@dataclass(frozen=True)
class QueueSnapshot:
    has_queue_record: bool
    queue_number: str
    status: str
    now_serving: str | None
    people_ahead: int
    estimated_wait_minutes: int
    claim_status: str | None
    requirements: str
    document_available: bool


@dataclass(frozen=True)
class AssistantData:
    resident: object
    intents: frozenset[str]
    services: tuple = field(default_factory=tuple)
    service_configurations: dict = field(default_factory=dict)
    active_appointments: tuple = field(default_factory=tuple)
    transactions: tuple = field(default_factory=tuple)
    events: tuple = field(default_factory=tuple)
    event_registrations: tuple = field(default_factory=tuple)
    knowledge: tuple = field(default_factory=tuple)
    notifications: tuple = field(default_factory=tuple)

    @property
    def primary_appointment(self):
        return self.active_appointments[0] if self.active_appointments else None


def classify_inquiry(message):
    """Return coarse data needs without using an external model."""
    text = " ".join(re.findall(r"[a-z0-9]+", message.lower()))
    intents = set()
    if any(term in text for term in ("fee", "cost", "price", "how much", "pila ang bayad", "pila bayad", "tagpila", "magkano", "bayad")):
        intents.add("service_fee")
    if any(term in text for term in ("requirement", "what do i need", "what should i bring", "dalhon", "kinahanglan", "kailangan", "requirements")):
        intents.add("service_requirements")
    if any(term in text for term in ("service", "available", "serbisyo", "ano ang meron", "unsa ang naa")):
        intents.add("service_availability")
    if any(term in text for term in ("book", "booking", "mag book", "magbook", "pag book", "unsaon", "paano")):
        intents.add("booking_help")
    if intents & {"service_fee", "service_requirements", "service_availability", "booking_help"} or "clearance" in text:
        intents.add("services")
    if any(term in text for term in ("office hour", "opening hour", "when are you open", "what time do you open", "oras ng opisina", "anong oras", "oras sa opisina", "kanus a abli", "kanus a mo mag open", "kanus a mo abli", "bukas ba")):
        intents.add("office")
    if any(term in text for term in ("cancel", "kanselahin", "kanselahon", "cancelon")):
        intents.add("appointment_cancel")
    if any(term in text for term in ("check in", "checkin", "mag check in", "pag check in")):
        intents.add("appointment_checkin")
    if any(term in text for term in ("appointment status", "status sa akong appointment", "status ng appointment", "track", "appointment ko", "akong appointment", "appointment ba ako", "may appointment", "naa koy appointment", "next appointment", "sunod appointment")):
        intents.add("appointment_status")
    if any(term in text for term in ("transaction", "history", "previous", "past", "kasaysayan", "nakaraang", "mga transaksyon")):
        intents.add("transactions")
    if intents & {"appointment_cancel", "appointment_checkin", "appointment_status", "transactions"} or "appointment" in text:
        intents.add("appointments")
    if any(term in text for term in ("queue number", "numero sa queue", "numero ng queue", "akong numero", "number ko")):
        intents.add("queue_number")
    if any(term in text for term in ("people ahead", "ahead of me", "how many are ahead", "pila pa", "pila ang una", "ilan pa", "ilan ang nauna", "queue position", "posisyon sa queue")):
        intents.add("queue_position")
    if any(term in text for term in ("wait", "waiting time", "how long", "gaano katagal", "matagal", "hulat", "dugay")):
        intents.add("queue_wait")
    if intents & {"queue_number", "queue_position", "queue_wait"} or "queue" in text or "linya" in text:
        intents.update(("appointments", "queue"))
    if any(term in text for term in ("pickup", "pick up", "claim", "ready", "release", "released", "makuha", "makukuha", "kuhaon", "kunin", "pwede nako makuha", "ready na")):
        intents.add("document_pickup")
    if any(term in text for term in ("document status", "processing", "dokumento", "document")):
        intents.add("document_status")
    if intents & {"document_pickup", "document_status"}:
        intents.update(("appointments", "documents"))
    if any(term in text for term in ("registration status", "registered", "registration ko", "rehistro", "nagparehistro", "booking reference", "qr pass")):
        intents.add("event_registration")
    if any(term in text for term in ("event", "special service", "temporary service", "kaganapan", "kalihokan")):
        intents.add("event_availability")
    if intents & {"event_registration", "event_availability"}:
        intents.add("events")
    if "notification" in text or "abiso" in text or "pahibalo" in text:
        intents.add("notifications")
    if any(term in text for term in ("help", "tabang", "tulong", "navigate", "asa makita", "saan makikita", "home tab", "book tab", "queue tab", "transactions tab", "profile tab")):
        intents.add("general_help")
    if not intents:
        intents.add("knowledge")
    return frozenset(intents)


def available_services_for(resident):
    """Return only permanent services or temporary services owned by the resident's barangay."""
    configurations = {
        item.service_id: item
        for item in BarangayServiceConfiguration.objects.filter(barangay=resident.barangay)
    }
    services = Service.objects.filter(is_active=True).filter(
        Q(is_temporary=False)
        | Q(
            is_temporary=True,
            barangay=resident.barangay,
            lifecycle=Service.Lifecycle.SCHEDULED,
        )
    ).order_by("name")
    visible = []
    for service in services:
        configuration = configurations.get(service.pk)
        if not service.is_temporary and configuration and not configuration.is_active:
            continue
        visible.append(service)
    return tuple(visible), configurations


def active_appointments_for(resident, limit=5):
    tickets = QueueTicket.objects.select_related("generated_document").order_by("pk")
    return tuple(
        resident.appointments.select_related("service", "barangay", "time_slot", "event_booking")
        .prefetch_related(Prefetch("queue_ticket", queryset=tickets))
        .filter(
            Q(appointment_date__gte=timezone.localdate()) | Q(appointment_date__isnull=True),
            status__in=ACTIVE_APPOINTMENT_STATUSES,
        )
        .order_by(
            F("appointment_date").asc(nulls_last=True),
            F("time_slot__start_time").asc(nulls_last=True),
            "created_at",
        )[:limit]
    )


def transactions_for(resident, limit=10):
    return tuple(
        resident.appointments.select_related(
            "service", "barangay", "time_slot", "queue_ticket", "queue_ticket__generated_document", "event_booking"
        ).order_by("-created_at")[:limit]
    )


def events_for(resident):
    today = timezone.localdate()
    events = tuple(
        Service.objects.filter(
            is_active=True,
            is_temporary=True,
            barangay=resident.barangay,
            lifecycle=Service.Lifecycle.SCHEDULED,
        ).filter(Q(event_end_date__gte=today) | Q(event_end_date__isnull=True)).order_by("event_start_date", "name")[:10]
    )
    registrations = tuple(
        EventBooking.objects.select_related("appointment__service")
        .filter(appointment__resident=resident, appointment__service__barangay=resident.barangay)
        .order_by("-created_at")[:10]
    )
    return events, registrations


def queue_snapshot_for(appointment, configurations=None):
    """Calculate position from authoritative QueueTicket creation order, never queue-number text."""
    try:
        ticket = appointment.queue_ticket
    except QueueTicket.DoesNotExist:
        ticket = None
    if ticket is None:
        return QueueSnapshot(
            has_queue_record=False,
            queue_number=(appointment.queue_number or "").strip(),
            status="Not recorded",
            now_serving=None,
            people_ahead=0,
            estimated_wait_minutes=0,
            claim_status=None,
            requirements="",
            document_available=False,
        )

    same_queue = QueueTicket.objects.filter(
        appointment__appointment_date=appointment.appointment_date,
        appointment__barangay=appointment.barangay,
        appointment__service=appointment.service,
    )
    active_queue = same_queue.filter(status__in=ACTIVE_QUEUE_STATUSES)
    people_ahead = 0
    if ticket.status == QueueTicket.Status.WAITING:
        people_ahead = active_queue.exclude(pk=ticket.pk).filter(
            Q(status=QueueTicket.Status.NOW_SERVING)
            | Q(status=QueueTicket.Status.WAITING, pk__lt=ticket.pk)
        ).count()
    now_serving = active_queue.filter(status=QueueTicket.Status.NOW_SERVING).order_by(
        F("called_at").asc(nulls_last=True), "pk"
    ).first()
    configuration = (configurations or {}).get(appointment.service_id)
    duration = configuration.estimated_duration if configuration else appointment.service.estimated_duration
    try:
        document_available = bool(ticket.generated_document_id)
    except AttributeError:
        document_available = hasattr(ticket, "generated_document")
    return QueueSnapshot(
        has_queue_record=True,
        queue_number=(ticket.queue_number or appointment.queue_number or "").strip(),
        status=ticket.get_status_display(),
        now_serving=now_serving.queue_number if now_serving else None,
        people_ahead=people_ahead,
        estimated_wait_minutes=people_ahead * duration,
        claim_status=ticket.get_claim_status_display() if ticket.claim_status else None,
        requirements=ticket.requirements.strip(),
        document_available=document_available,
    )


def service_fee_for(service, configurations):
    configuration = configurations.get(service.pk)
    if configuration:
        return configuration.fee
    return None if service.is_temporary else Decimal("0.00")


def assistant_data_for(resident, message):
    intents = classify_inquiry(message)
    services = ()
    configurations = {}
    active_appointments = ()
    transactions = ()
    events = ()
    registrations = ()
    knowledge = ()
    notifications = ()

    if intents & {"services", "queue", "documents"}:
        services, configurations = available_services_for(resident)
    if intents & {"appointments", "queue", "documents"}:
        active_appointments = active_appointments_for(resident)
    if "transactions" in intents:
        transactions = transactions_for(resident)
    if "documents" in intents and not transactions:
        transactions = transactions_for(resident)
    if "events" in intents:
        events, registrations = events_for(resident)
    if "notifications" in intents:
        notifications = tuple(resident.notifications.order_by("-created_at")[:3])
    if "knowledge" in intents:
        knowledge = tuple(
            AssistantKnowledge.objects.filter(
                Q(barangay__isnull=True) | Q(barangay=resident.barangay), is_approved=True
            ).order_by("title")[:10]
        )

    return AssistantData(
        resident=resident,
        intents=intents,
        services=services,
        service_configurations=configurations,
        active_appointments=active_appointments,
        transactions=transactions,
        events=events,
        event_registrations=registrations,
        knowledge=knowledge,
        notifications=notifications,
    )


def money_label(value):
    if value is None:
        return "not recorded"
    value = Decimal(value)
    return "Free" if value == 0 else f"PHP {value:,.2f}"


def office_hours():
    return settings.QUICKQUEUE_OFFICE_HOURS
