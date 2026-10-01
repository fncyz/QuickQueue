import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.db import transaction

from qq.models import PushDelivery

logger = logging.getLogger(__name__)
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def queue_notification_push(notification):
    """Send once per resident device after the notification transaction commits."""
    transaction.on_commit(lambda: _send_notification_push(notification.pk))


def _send_notification_push(notification_id):
    from qq.models import Notification

    try:
        notification = Notification.objects.select_related("appointment").get(pk=notification_id)
    except Notification.DoesNotExist:
        return

    for device in notification.resident.push_devices.filter(is_active=True):
        delivery, created = PushDelivery.objects.get_or_create(notification=notification, device=device)
        if not created:
            continue
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
