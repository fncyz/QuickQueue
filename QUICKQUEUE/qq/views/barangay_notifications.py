from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
import json
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from qq.models import Barangay, BarangayStaff, Notification
from qq.services.notification_service import notifications_for_user


def _barangay_for(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        return user.staff_profile.barangay
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error


@login_required(login_url="signin")
def barangay_notifications(request):
    barangay = _barangay_for(request.user)
    is_regular_staff = (
        hasattr(request.user, "staff_profile")
        and request.user.staff_profile.role != BarangayStaff.Role.ADMIN
        and not hasattr(request.user, "barangay_profile")
    )
    role = Notification.RecipientRole.STAFF if is_regular_staff else Notification.RecipientRole.ADMIN
    notifications = notifications_for_user(
        request.user, role,
    ).filter(barangay=barangay).select_related("resident", "appointment").order_by("-created_at")
    all_count = notifications.count()

    if request.method == "POST":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            try:
                payload = json.loads(request.body or "{}")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid request."}, status=400)
            notification_id = payload.get("notification_id")
            target = notifications.filter(pk=notification_id) if notification_id else notifications
            updated = target.filter(is_read=False).update(is_read=True, admin_is_read=True)
            return JsonResponse({"updated": updated, "unread_count": notifications.filter(is_read=False).count()})
        updated = notifications.filter(is_read=False).update(is_read=True, admin_is_read=True)
        messages.success(request, f"Marked {updated} notification{'s' if updated != 1 else ''} as read.")
        return redirect("barangay_notifications")

    search = request.GET.get("q", "").strip()
    unread_only = request.GET.get("filter") == "unread"
    if search:
        notifications = notifications.filter(Q(title__icontains=search) | Q(message__icontains=search))
    if unread_only:
        notifications = notifications.filter(is_read=False)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
        items = notifications[:20]
        return JsonResponse({
            "total_count": all_count,
            "unread_count": notifications_for_user(request.user, role).filter(barangay=barangay, is_read=False).count(),
            "history_url": request.path,
            "notifications": [{
                "id": item.pk, "type": item.notification_type, "title": item.title,
                "message": item.message, "is_read": item.is_read,
                "created_at": item.created_at.isoformat(),
                "url": (
                    reverse("staff_live_queue") if is_regular_staff and item.notification_type == Notification.NotificationType.STAFF_ALERT
                    else reverse("barangay_live_queue") if not is_regular_staff and item.notification_type == Notification.NotificationType.QUEUE_UPDATE
                    else reverse("staff_appointments") if is_regular_staff
                    else reverse("barangay_appointments")
                ),
            } for item in items],
        })

    paginator = Paginator(notifications, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "barangay_admin/notifications.html", {
        "barangay": barangay,
        "today": timezone.localdate(),
        "notifications": page_obj,
        "page_obj": page_obj,
        "is_regular_staff": is_regular_staff,
        "search": search,
        "active_filter": "unread" if unread_only else "all",
        "unread_notifications": notifications.filter(is_read=False).count(),
    })
