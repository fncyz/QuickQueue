from django.db.models.signals import post_save
from django.dispatch import receiver

from qq.models import Notification
from qq.services.push_notifications import queue_notification_push


@receiver(post_save, sender=Notification)
def send_new_notification_push(sender, instance, created, **kwargs):
    if created:
        queue_notification_push(instance)
