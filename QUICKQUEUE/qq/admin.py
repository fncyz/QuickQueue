from django.contrib import admin
from .models import (Barangay, Service, Resident,
                     Appointment, QueueTicket, Notification, TimeSlot,
                     BarangayAdminRegistration, BarangayStaff, DocumentTemplate, GeneratedDocument)
from django.utils import timezone
from django.db import transaction


@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "contact_number",
        "email",
        "is_active",
    )

    search_fields = (
        "name",
        "email",
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "estimated_duration",
        "is_active",
    )


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "first_name",
        "last_name",
        "barangay",
        "email",
        "contact_number",
    )

    list_filter = (
        "barangay",
        "sex",
    )

    search_fields = (
        "user__username",
        "first_name",
        "last_name",
        "email",
        "contact_number",
    )

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "resident",
        "barangay",
        "service",
        "appointment_date",
        "time_slot",
        "queue_number",
        "sitio",
        "status",
    )

    list_filter = (
        "status",
        "appointment_date",
    )

    search_fields = (
        "resident__first_name",
        "resident__last_name",
        "sitio",
        "queue_number",
    )

    ordering = (
        "appointment_date",
        "time_slot",
    )

@admin.register(QueueTicket)
class QueueTicketAdmin(admin.ModelAdmin):
    list_display = (
        "queue_number",
        "appointment",
        "status",
        "called_at",
        "completed_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "queue_number",
        "appointment__resident__first_name",
        "appointment__resident__last_name",
    )

    ordering = (
        "queue_number",
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "resident",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
    )

    search_fields = (
        "resident__first_name",
        "resident__last_name",
        "title",
    )

    ordering = (
        "-created_at",
    )

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = (
        "barangay",
        "start_time",
        "end_time",
        "max_appointments",
        "is_active",
    )

    list_filter = (
        "barangay",
        "is_active",
    )

    ordering = (
        "barangay",
        "start_time",
    )


@admin.register(BarangayAdminRegistration)
class BarangayAdminRegistrationAdmin(admin.ModelAdmin):
    list_display = ("barangay", "user", "contact_number", "email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("barangay__name", "user__username", "email", "contact_number")
    readonly_fields = ("created_at", "terms_accepted_at", "reviewed_at")
    actions = ("approve_registrations", "reject_registrations")

    @admin.action(description="Approve selected barangay admin registrations")
    def approve_registrations(self, request, queryset):
        approved = 0
        for registration in queryset.select_related("user", "barangay"):
            if registration.status != BarangayAdminRegistration.Status.PENDING or registration.barangay.user_id:
                continue
            with transaction.atomic():
                registration.user.is_active = True
                registration.user.is_staff = True
                registration.user.save(update_fields=("is_active", "is_staff"))
                registration.barangay.user = registration.user
                registration.barangay.address = registration.complete_address
                registration.barangay.contact_number = registration.contact_number
                registration.barangay.email = registration.email
                registration.barangay.save(update_fields=("user", "address", "contact_number", "email", "updated_at"))
                registration.status = BarangayAdminRegistration.Status.APPROVED
                registration.reviewed_at = timezone.now()
                registration.save(update_fields=("status", "reviewed_at"))
                BarangayStaff.objects.update_or_create(
                    barangay=registration.barangay,
                    user=registration.user,
                    defaults={
                        "first_name": registration.user.first_name or registration.user.username,
                        "last_name": registration.user.last_name or "Admin",
                        "username": registration.user.username,
                        "email": registration.email,
                        "contact_number": registration.contact_number,
                        "role": BarangayStaff.Role.ADMIN,
                        "is_active": True,
                    },
                )
                approved += 1
        self.message_user(request, f"Approved {approved} registration(s).")


@admin.register(BarangayStaff)
class BarangayStaffAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "username",
        "barangay",
        "role",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_active", "barangay")
    search_fields = ("first_name", "last_name", "username", "email", "contact_number")

    @admin.action(description="Reject selected barangay admin registrations")
    def reject_registrations(self, request, queryset):
        rejected = queryset.filter(status=BarangayAdminRegistration.Status.PENDING).update(
            status=BarangayAdminRegistration.Status.REJECTED,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"Rejected {rejected} registration(s).")


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "barangay", "service", "version", "is_active", "updated_at")
    list_filter = ("barangay", "is_active")
    search_fields = ("name", "service__name")


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "template", "status", "generated_at", "archived_at")
    list_filter = ("status",)
