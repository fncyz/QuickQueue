import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.db import transaction

from qq.models import PushDelivery

logger = logging.getLogger(__name__)
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def queue_notification_push(notification):
    """Deliver after commit so push failure can never roll back domain data."""
    notification_id = notification.pk
    transaction.on_commit(lambda: _send_notification_push_safely(notification_id))


def _send_notification_push_safely(notification_id):
    try:
        _send_notification_push(notification_id)
    except Exception:
        logger.exception("Unexpected push delivery failure for notification %s", notification_id)


def _send_notification_push(notification_id):
    from qq.models import Notification

    try:
        notification = Notification.objects.select_related("appointment", "resident").get(pk=notification_id)
    except Notification.DoesNotExist:
        return

    if notification.recipient_role != Notification.RecipientRole.RESIDENT or not notification.resident_id:
        return

    for device in notification.resident.push_devices.filter(is_active=True):
        delivery, created = PushDelivery.objects.get_or_create(notification=notification, device=device)
        if not created and delivery.expo_ticket_id:
            continue
        if not created:
            delivery.error = ""
        payload = {
            "to": device.expo_push_token,
            "title": notification.title[:100],
            "body": " ".join(notification.message.split())[:240],
            "sound": "default",
            "priority": "high" if notification.notification_type == "QU" else "default",
            "channelId": "queue-alerts" if notification.notification_type == "QU" else "appointment-updates",
            "data": {
                "eventId": str(notification.pk),
                "type": notification.notification_type,
                "appointmentId": notification.appointment_id,
                "route": (
                    "queue" if notification.notification_type == "QU"
                    else "transactions"
                ),
            },
        }
        request = Request(
            EXPO_PUSH_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8")).get("data", {})
            if result.get("status") == "ok":
                delivery.expo_ticket_id = result.get("id", "")
            else:
                delivery.error = result.get("message", "Expo rejected the push notification.")
                if result.get("details", {}).get("error") == "DeviceNotRegistered":
                    device.is_active = False
                    device.save(update_fields=["is_active", "updated_at"])
            delivery.save(update_fields=["expo_ticket_id", "error"])
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            delivery.error = str(error)[:1000]
            delivery.save(update_fields=["error"])
            logger.warning("Push delivery failed for device %s: %s", device.pk, error)
