from difflib import SequenceMatcher
import re

from django.utils import timezone

from qq.models import Appointment, QueueTicket
from qq.services.assistant_data import money_label, office_hours, queue_snapshot_for, service_fee_for


def _say(language, *, en, fil, ceb):
    return {"en": en, "fil": fil, "ceb": ceb}[language.base]


def _tokens(value):
    return re.findall(r"[a-z0-9]+", value.lower())


def _service_from_conversation(message, services, history):
    searchable = [message]
    searchable.extend(
        item.get("text", "") for item in reversed(history or []) if item.get("role") == "resident"
    )
    ignored = {"a", "an", "ang", "for", "of", "the", "to", "sa", "ng", "mga"}
    for text in searchable:
        message_tokens = _tokens(text)
        best, best_score = None, 0.0
        for service in services:
            service_tokens = [token for token in _tokens(service.name) if token not in ignored]
            if not service_tokens:
                continue
            matches = sum(
                any(SequenceMatcher(None, target, source).ratio() >= 0.80 for source in message_tokens)
                for target in service_tokens
            )
            score = matches / len(service_tokens)
            if score > best_score:
                best, best_score = service, score
        if best_score >= 0.60:
            return best
    return None


def _item_from_conversation(message, items, history):
    """Resolve an appointment/transaction by its official service name."""
    services = [item.service for item in items]
    service = _service_from_conversation(message, services, history)
    if service is None:
        return None
    return next((item for item in items if item.service_id == service.pk), None)


def _service_choices(items):
    return ", ".join(dict.fromkeys(item.service.name for item in items))


def deterministic_reply(message, data, language, history=None):
    """Return a localized verified answer, or None when Gemini should handle the inquiry."""
    intents = data.intents
    services = list(data.services)
    service = _service_from_conversation(message, services, history)

    if "booking_help" in intents:
        return _say(language,
            en="To book an appointment:\n\n1. Open the Book tab.\n\n2. Select a service.\n\n3. Choose an available date and time.\n\n4. Review the details and submit.",
            fil="Para mag-book ng appointment:\n\n1. Buksan ang Book tab.\n\n2. Piliin ang serbisyo.\n\n3. Pumili ng available na petsa at oras.\n\n4. Suriin ang detalye at i-submit.",
            ceb="Aron mag-book og appointment:\n\n1. Ablihi ang Book tab.\n\n2. Pilia ang serbisyo.\n\n3. Pilia ang available nga petsa ug oras.\n\n4. Ribyuha ang detalye ug i-submit.")

    if "service_fee" in intents:
        if not service:
            return _say(language,
                en="Which service fee would you like to check?",
                fil="Aling serbisyo ang gusto mong tingnan ang bayad?",
                ceb="Asang serbisyo ang gusto nimong susihon ang bayad?")
        fee = money_label(service_fee_for(service, data.service_configurations)).replace("PHP ", "₱")
        return _say(language,
            en=f"The {service.name} fee is {fee}.",
            fil=f"Ang bayad sa {service.name} ay {fee}.",
            ceb=f"Ang bayad sa {service.name} kay {fee}.")

    if "service_requirements" in intents:
        if not service:
            return _say(language,
                en="Which service do you need the requirements for?",
                fil="Para sa aling serbisyo ang requirements na kailangan mo?",
                ceb="Para sa asang serbisyo ang requirements nga imong kinahanglan?")
        requirements = service.requirements.strip()
        if not requirements:
            return _say(language,
                en=f"QuickQueue does not currently list requirements for {service.name}.",
                fil=f"Walang nakalistang requirements sa QuickQueue para sa {service.name}.",
                ceb=f"Walay nakalistang requirements sa QuickQueue para sa {service.name}.")
        return _say(language,
            en=f"The requirements for {service.name} are: {requirements}",
            fil=f"Ang requirements para sa {service.name} ay: {requirements}",
            ceb=f"Ang requirements para sa {service.name} kay: {requirements}")

    if "service_availability" in intents:
        names = ", ".join(item.name for item in services)
        if not names:
            return _say(language, en="No active services are currently listed for your barangay.", fil="Walang kasalukuyang active na serbisyo para sa inyong barangay.", ceb="Walay active nga serbisyo nga nakalista karon para sa inyong barangay.")
        return _say(language, en=f"The services available for your barangay are: {names}.", fil=f"Ang mga serbisyong available sa inyong barangay ay: {names}.", ceb=f"Ang mga serbisyong available sa inyong barangay kay: {names}.")

    if "office" in intents:
        hours = office_hours()
        return _say(language, en=f"QuickQueue office hours are {hours}", fil=f"Ang oras ng opisina sa QuickQueue ay {hours}", ceb=f"Ang oras sa opisina sa QuickQueue kay {hours}")

    appointment = _item_from_conversation(message, data.active_appointments, history) or data.primary_appointment
    asks_for_next = any(term in " ".join(_tokens(message)) for term in ("next", "sunod", "bukas", "ugma"))
    if len(data.active_appointments) > 1 and not asks_for_next and intents & {
        "appointment_status", "appointment_cancel", "queue_number", "queue_position", "queue_wait"
    } and _item_from_conversation(message, data.active_appointments, history) is None:
        choices = _service_choices(data.active_appointments)
        return _say(language,
            en=f"You have multiple active appointments: {choices}. Which appointment do you mean?",
            fil=f"Mayroon kang maraming active appointment: {choices}. Aling appointment ang tinutukoy mo?",
            ceb=f"Aduna kay daghang active appointment: {choices}. Asa nga appointment imong pasabot?")
    if "appointment_status" in intents:
        if not appointment:
            return _say(language, en="You don't have an active appointment at the moment.", fil="Wala kang active na appointment sa ngayon.", ceb="Wala kay active nga appointment karon.")
        status = appointment.get_status_display()
        date_detail = appointment.appointment_date.strftime("%B %d, %Y") if appointment.appointment_date else None
        return _say(language,
            en=f"Your {appointment.service.name} appointment is {status}. {f'It is scheduled for {date_detail}.' if date_detail else 'Its date has not been assigned yet.'}",
            fil=f"Ang status ng iyong {appointment.service.name} appointment ay {status}. {f'Naka-schedule ito sa {date_detail}.' if date_detail else 'Wala pang nakatalagang petsa.'}",
            ceb=f"Ang status sa imong {appointment.service.name} appointment kay {status}. {f'Naka-schedule kini sa {date_detail}.' if date_detail else 'Wala pa kini ma-assign og petsa.'}")

    if "appointment_cancel" in intents:
        if not appointment:
            return _say(language, en="You don't have an active appointment to cancel.", fil="Wala kang active na appointment na maaaring kanselahin.", ceb="Wala kay active nga appointment nga makansela.")
        allowed = appointment.status in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED) and (appointment.appointment_date is None or appointment.appointment_date >= timezone.localdate())
        if not allowed:
            return _say(language, en=f"Your {appointment.service.name} appointment can no longer be cancelled in the app.", fil=f"Hindi na maaaring kanselahin sa app ang iyong {appointment.service.name} appointment.", ceb=f"Dili na makansela sa app ang imong {appointment.service.name} appointment.")
        return _say(language, en="Open the appointment in Queue or Transactions, tap Cancel Appointment, and confirm.", fil="Buksan ang appointment sa Queue o Transactions, i-tap ang Cancel Appointment, at kumpirmahin.", ceb="Ablihi ang appointment sa Queue o Transactions, i-tap ang Cancel Appointment, ug kumpirmaha.")

    if "appointment_checkin" in intents:
        if not appointment:
            return _say(language, en="You don't have an active appointment to check in for.", fil="Wala kang active na appointment na maaaring i-check in.", ceb="Wala kay active nga appointment nga ma-check in.")
        if appointment.appointment_date is None:
            return _say(language, en="Your appointment date and time have not been assigned yet. Check Queue or contact barangay staff before checking in.", fil="Hindi pa naitalaga ang petsa at oras ng appointment mo. Tingnan ang Queue o makipag-ugnayan sa barangay staff bago mag-check in.", ceb="Wala pa ma-assign ang petsa ug oras sa imong appointment. Tan-awa ang Queue o kontaka ang barangay staff sa dili pa mag-check in.")
        if appointment.appointment_date != timezone.localdate():
            date_text = appointment.appointment_date.strftime("%B %d, %Y")
            return _say(language, en=f"Check-in is available on {date_text}. On that date, open Queue and tap Check In.", fil=f"Available ang check-in sa {date_text}. Sa araw na iyon, buksan ang Queue at i-tap ang Check In.", ceb=f"Available ang check-in sa {date_text}. Nianang adlawa, ablihi ang Queue ug i-tap ang Check In.")
        return _say(language, en="Open Queue, find Appointment Actions, and tap Check In.", fil="Buksan ang Queue, hanapin ang Appointment Actions, at i-tap ang Check In.", ceb="Ablihi ang Queue, pangitaa ang Appointment Actions, ug i-tap ang Check In.")

    if intents & {"queue_number", "queue_position", "queue_wait"}:
        if not appointment:
            return _say(language, en="You don't have an active appointment with queue information.", fil="Wala kang active na appointment na may queue information.", ceb="Wala kay active nga appointment nga adunay queue information.")
        snapshot = queue_snapshot_for(appointment, data.service_configurations)
        if not snapshot.queue_number:
            return _say(language, en="Your queue number has not been assigned yet.", fil="Hindi pa naitalaga ang iyong queue number.", ceb="Wala pa ma-assign ang imong queue number.")
        if "queue_wait" in intents:
            if not snapshot.has_queue_record or snapshot.status not in {
                QueueTicket.Status.WAITING.label, QueueTicket.Status.NOW_SERVING.label
            }:
                return _say(language,
                    en=f"QuickQueue cannot provide a reliable waiting-time estimate for {appointment.service.name} yet. Check the Queue tab after your queue record becomes active.",
                    fil=f"Wala pang maaasahang waiting-time estimate sa QuickQueue para sa {appointment.service.name}. Tingnan ang Queue tab kapag active na ang queue record mo.",
                    ceb=f"Wala pay kasaligan nga waiting-time estimate sa QuickQueue para sa {appointment.service.name}. Tan-awa ang Queue tab kung active na ang imong queue record.")
            return _say(language, en=f"Your estimated waiting time is {snapshot.estimated_wait_minutes} minutes, with {snapshot.people_ahead} ahead of you.", fil=f"Ang tinatayang oras ng paghihintay mo ay {snapshot.estimated_wait_minutes} minuto, at may {snapshot.people_ahead} na nauna sa iyo.", ceb=f"Ang gibanabanang hulat nimo kay {snapshot.estimated_wait_minutes} minutos, ug adunay {snapshot.people_ahead} nga nauna nimo.")
        if "queue_position" in intents:
            if not snapshot.has_queue_record:
                return _say(language, en="Your queue position is not available yet.", fil="Hindi pa available ang posisyon mo sa queue.", ceb="Wala pa available ang imong posisyon sa queue.")
            return _say(language, en=f"There are {snapshot.people_ahead} ahead of you in the queue.", fil=f"May {snapshot.people_ahead} na nauna sa iyo sa queue.", ceb=f"Adunay {snapshot.people_ahead} nga nauna nimo sa queue.")
        return _say(language, en=f"Your queue number is {snapshot.queue_number}, and its status is {snapshot.status}.", fil=f"Ang queue number mo ay {snapshot.queue_number}, at ang status nito ay {snapshot.status}.", ceb=f"Ang imong queue number kay {snapshot.queue_number}, ug ang status niini kay {snapshot.status}.")

    if intents & {"document_status", "document_pickup"}:
        if not data.transactions:
            return _say(language, en="You do not have a document transaction recorded in QuickQueue.", fil="Wala kang document transaction na nakatala sa QuickQueue.", ceb="Wala kay document transaction nga nakarekord sa QuickQueue.")
        transaction = _item_from_conversation(message, data.transactions, history)
        snapshots = {
            item.pk: queue_snapshot_for(item, data.service_configurations)
            for item in data.transactions
        }
        document_candidates = [item for item in data.transactions if snapshots[item.pk].claim_status]
        if transaction is None and len(document_candidates) > 1:
            choices = _service_choices(document_candidates)
            return _say(language,
                en=f"You have multiple document transactions: {choices}. Which document do you mean?",
                fil=f"Mayroon kang maraming document transaction: {choices}. Aling document ang tinutukoy mo?",
                ceb=f"Aduna kay daghang document transaction: {choices}. Asa nga document imong pasabot?")
        transaction = transaction or (document_candidates[0] if document_candidates else data.transactions[0])
        snapshot = snapshots[transaction.pk]
        if not snapshot.claim_status:
            return _say(language, en=f"QuickQueue does not currently list a document pickup status for {transaction.service.name}.", fil=f"Wala pang nakalistang document pickup status sa QuickQueue para sa {transaction.service.name}.", ceb=f"Wala pay nakalistang document pickup status sa QuickQueue para sa {transaction.service.name}.")
        return _say(language, en=f"The document status for {transaction.service.name} is {snapshot.claim_status}.", fil=f"Ang document status para sa {transaction.service.name} ay {snapshot.claim_status}.", ceb=f"Ang document status para sa {transaction.service.name} kay {snapshot.claim_status}.")

    if intents & {"event_availability", "event_registration"}:
        if "event_registration" in intents and data.event_registrations:
            registration = data.event_registrations[0]
            name = registration.appointment.service.name
            return _say(language, en=f"Your {name} registration is {registration.get_status_display()}, with booking reference {registration.booking_reference}.", fil=f"Ang registration mo sa {name} ay {registration.get_status_display()}, na may booking reference na {registration.booking_reference}.", ceb=f"Ang imong registration sa {name} kay {registration.get_status_display()}, nga adunay booking reference nga {registration.booking_reference}.")
        if "event_registration" in intents:
            return _say(language,
                en="You do not have an event registration recorded in QuickQueue.",
                fil="Wala kang event registration na nakatala sa QuickQueue.",
                ceb="Wala kay event registration nga nakarekord sa QuickQueue.")
        names = ", ".join(event.name for event in data.events)
        if not names:
            return _say(language, en="No current events or temporary services are listed for your barangay.", fil="Walang kasalukuyang event o temporary service para sa inyong barangay.", ceb="Walay event o temporary service nga nakalista karon para sa inyong barangay.")
        return _say(language, en=f"The events and temporary services for your barangay are: {names}.", fil=f"Ang mga event at temporary service para sa inyong barangay ay: {names}.", ceb=f"Ang mga event ug temporary service para sa inyong barangay kay: {names}.")

    if "transactions" in intents:
        if not data.transactions:
            return _say(language, en="You don't have any transactions recorded yet.", fil="Wala ka pang nakatalang transaction.", ceb="Wala pa kay transaction nga nakarekord.")
        summary = ", ".join(f"{item.service.name} ({item.get_status_display()})" for item in data.transactions[:5])
        return _say(language, en=f"Your recent transactions are: {summary}.", fil=f"Ang mga recent transaction mo ay: {summary}.", ceb=f"Ang imong bag-ong mga transaction kay: {summary}.")

    if "general_help" in intents:
        normalized = " ".join(_tokens(message))
        destinations = (
            (("book tab", "book"), "Book", "booking a service"),
            (("queue tab", "queue"), "Queue", "active appointments and queue updates"),
            (("transactions tab", "transaction"), "Transactions", "appointment history and document status"),
            (("profile tab", "profile"), "Profile", "account settings"),
            (("notification", "abiso", "pahibalo"), "Notifications", "recent updates"),
        )
        destination = next(((tab, purpose) for terms, tab, purpose in destinations if any(term in normalized for term in terms)), None)
        if destination:
            tab, purpose = destination
            return _say(language,
                en=f"Open the {tab} section to view {purpose}.",
                fil=f"Buksan ang {tab} section para makita ang {purpose}.",
                ceb=f"Ablihi ang {tab} section aron makita ang {purpose}.")
        return _say(language, en="I can help with services, appointments, queues, documents, events, office hours, and QuickQueue navigation.", fil="Makakatulong ako sa services, appointments, queues, documents, events, office hours, at pag-navigate sa QuickQueue.", ceb="Makatabang ko sa services, appointments, queues, documents, events, office hours, ug pag-navigate sa QuickQueue.")
    return None


def provider_failure_reply(language):
    return _say(language,
        en="I can still help with verified QuickQueue services, appointments, queues, documents, events, and office hours. Please ask about one of these topics.",
        fil="Makakatulong pa rin ako gamit ang verified na impormasyon tungkol sa QuickQueue services, appointments, queues, documents, events, at office hours. Magtanong tungkol sa isa sa mga ito.",
        ceb="Makatabang gihapon ko gamit ang verified nga impormasyon bahin sa QuickQueue services, appointments, queues, documents, events, ug office hours. Pangutana bahin sa usa niini.")
