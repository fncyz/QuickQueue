from qq.models import BarangayStaff, Notification


def staff_notification_state(request):
    """Expose one recipient-scoped unread state to every regular staff page."""
    user = request.user
    if not user.is_authenticated or hasattr(user, "barangay_profile"):
        return {}
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist:
        return {}
    if staff.role == BarangayStaff.Role.ADMIN:
        return {}
    return {
        "unread_notifications": Notification.objects.filter(
            recipient=user,
            recipient_role=Notification.RecipientRole.STAFF,
            barangay=staff.barangay,
            is_read=False,
        ).count(),
    }
