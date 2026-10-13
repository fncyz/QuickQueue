from django.contrib.auth.models import User

from qq.models import BarangayStaff, Notification


def _create_notification(*, recipient=None, recipient_id=None, role, barangay, appointment, notification_type, title, message, event_key):
    resolved_recipient_id = recipient_id or (recipient.pk if recipient else None)
    notification, _ = Notification.objects.get_or_create(
        event_key=event_key,
        defaults={
            "recipient_id": resolved_recipient_id,
            "recipient_role": role,
            "barangay": barangay,
            "resident": appointment.resident if role == Notification.RecipientRole.RESIDENT else None,
            "appointment": appointment,
            "notification_type": notification_type,
            "title": title,
            "message": message,
        },
    )
    return notification


def notify_resident(*, appointment, notification_type, title, message, event_key):
    return _create_notification(
        recipient=appointment.resident.user,
        role=Notification.RecipientRole.RESIDENT,
        barangay=appointment.barangay,
        appointment=appointment,
        notification_type=notification_type,
        title=title,
        message=message,
        event_key=f"resident:{appointment.resident.user_id}:{event_key}",
    )


def notify_barangay_staff(*, appointment, title, message, event_key):
    recipients = User.objects.filter(
        staff_profile__barangay=appointment.barangay,
        staff_profile__is_active=True,
        is_active=True,
    ).exclude(staff_profile__role=BarangayStaff.Role.ADMIN).distinct()
    return [
        _create_notification(
            recipient=user,
            role=Notification.RecipientRole.STAFF,
            barangay=appointment.barangay,
            appointment=appointment,
            notification_type=Notification.NotificationType.STAFF_ALERT,
            title=title,
            message=message,
            event_key=f"staff:{user.pk}:{event_key}",
        )
        for user in recipients
    ]


def notify_barangay_admins(*, barangay, title, message, event_key, appointment=None):
    user_ids = set(
        User.objects.filter(
            staff_profile__barangay=barangay,
            staff_profile__role=BarangayStaff.Role.ADMIN,
            staff_profile__is_active=True,
            is_active=True,
        ).values_list("pk", flat=True)
    )
    if barangay.user_id and barangay.user.is_active:
        user_ids.add(barangay.user_id)
    return [
        _create_notification(
            recipient_id=user_id,
            role=Notification.RecipientRole.ADMIN,
            barangay=barangay,
            appointment=appointment,
            notification_type=Notification.NotificationType.ADMIN_ALERT,
            title=title,
            message=message,
            event_key=f"admin:{user_id}:{event_key}",
        )
        for user_id in user_ids
    ]


def notifications_for_user(user, role=None):
    queryset = Notification.objects.filter(recipient=user)
    return queryset.filter(recipient_role=role) if role else queryset


def unread_count_for_user(user):
    return notifications_for_user(user).filter(is_read=False).count()
