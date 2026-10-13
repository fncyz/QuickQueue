from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import (AssistantKnowledge, Barangay, ChatFeedback, ChatQuestionTopic, Service, Resident,
                     Appointment, QueueTicket, Notification, TimeSlot,
                     BarangayAdministrator, BarangayAdminRegistration, BarangayStaff,
                     DocumentTemplate, GeneratedDocument)
from django.utils import timezone


class BarangayAdminForm(forms.ModelForm):
    class Meta:
        model = Barangay
        fields = "__all__"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicate = Barangay.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("A barangay with this name already exists.")
        return name


class BarangayAdministratorForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        required=False,
        help_text="Required for new accounts. Leave blank when editing to keep the current password.",
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = BarangayAdministrator
        fields = (
            "barangay", "first_name", "middle_name", "last_name", "username",
            "email", "contact_number", "profile_photo", "is_active",
        )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        users = User.objects.filter(username__iexact=username)
        if self.instance.pk and self.instance.user_id:
            users = users.exclude(pk=self.instance.user_id)
        if users.exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        users = User.objects.filter(email__iexact=email) if email else User.objects.none()
        if self.instance.pk and self.instance.user_id:
            users = users.exclude(pk=self.instance.user_id)
        if users.exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and not self.instance.user_id:
            raise forms.ValidationError(
                "This legacy profile has no linked user account and cannot be used to authenticate."
            )
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if not self.instance.pk and not password1:
            self.add_error("password1", "A password is required for new accounts.")
        if password1 != password2:
            self.add_error("password2", "The two password fields do not match.")
        elif password1:
            password_user = self.instance.user if self.instance.pk else User(
                username=cleaned_data.get("username", ""),
                email=cleaned_data.get("email", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
            )
            try:
                validate_password(password1, password_user)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data


class BarangayStaffAdminForm(forms.ModelForm):
    class Meta:
        model = BarangayStaff
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            choice for choice in BarangayStaff.Role.choices
            if choice[0] != BarangayStaff.Role.ADMIN
        ]


@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    form = BarangayAdminForm
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

    def has_add_permission(self, request):
        """Registration rows must only come from a terms-accepting submission."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Keep the registration and approval audit trail intact."""
        return False

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

    @admin.action(description="Reject selected barangay admin registrations")
    def reject_registrations(self, request, queryset):
        rejected = queryset.filter(status=BarangayAdminRegistration.Status.PENDING).update(
            status=BarangayAdminRegistration.Status.REJECTED,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"Rejected {rejected} registration(s).")


@admin.register(BarangayStaff)
class BarangayStaffAdmin(admin.ModelAdmin):
    form = BarangayStaffAdminForm
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

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(role=BarangayStaff.Role.ADMIN)


@admin.register(BarangayAdministrator)
class BarangayAdministratorAdmin(admin.ModelAdmin):
    form = BarangayAdministratorForm
    list_display = ("username", "full_name", "barangay", "email", "is_active", "created_at")
    list_filter = ("is_active", "barangay")
    search_fields = ("username", "first_name", "last_name", "email", "barangay__name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Barangay assignment", {"fields": ("barangay",)}),
        ("Administrator", {"fields": (
            "first_name", "middle_name", "last_name", "username", "email",
            "contact_number", "profile_photo",
        )}),
        ("Authentication", {"fields": ("password1", "password2", "is_active")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = fieldsets[:-1]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=BarangayStaff.Role.ADMIN).select_related("user", "barangay")

    def get_fieldsets(self, request, obj=None):
        return self.fieldsets if obj else self.add_fieldsets

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            raise PermissionDenied

        if change:
            user = obj.user
            if user is None:
                raise forms.ValidationError("This legacy profile has no linked user account.")
            user.username = obj.username
            user.first_name = obj.first_name
            user.last_name = obj.last_name
            user.email = obj.email
            user.is_active = obj.is_active
            if form.cleaned_data.get("password1"):
                user.set_password(form.cleaned_data["password1"])
            user.save()
            # Older approved accounts can also be linked through Barangay.user.
            # Detach that legacy pointer on reassignment so portal resolution uses
            # the newly selected BarangayStaff assignment instead of the old one.
            Barangay.objects.filter(user=user).exclude(pk=obj.barangay_id).update(user=None)
        else:
            user = User(
                username=obj.username,
                first_name=obj.first_name,
                last_name=obj.last_name,
                email=obj.email,
                is_active=obj.is_active,
                is_staff=False,
            )
            user.set_password(form.cleaned_data["password1"])
            user.save()
            obj.user = user

        obj.role = BarangayStaff.Role.ADMIN
        super().save_model(request, obj, form, change)

@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "barangay", "service", "version", "is_active", "updated_at")
    list_filter = ("barangay", "is_active")
    search_fields = ("name", "service__name")


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "template", "status", "generated_at", "archived_at")
    list_filter = ("status",)


@admin.register(AssistantKnowledge)
class AssistantKnowledgeAdmin(admin.ModelAdmin):
    list_display = ("title", "barangay", "is_approved", "updated_at")
    list_filter = ("is_approved", "barangay")
    search_fields = ("title", "content", "keywords")


@admin.register(ChatQuestionTopic)
class ChatQuestionTopicAdmin(admin.ModelAdmin):
    list_display = ("example_question", "count", "unanswered_count", "last_asked_at")
    readonly_fields = ("normalized_question", "example_question", "count", "unanswered_count", "last_asked_at")


@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    list_display = ("message", "helpful", "created_at")
    list_filter = ("helpful",)
    readonly_fields = ("message", "resident", "helpful", "created_at", "updated_at")
