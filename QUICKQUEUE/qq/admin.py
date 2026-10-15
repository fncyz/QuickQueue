from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import (AssistantKnowledge, Barangay, ChatFeedback, ChatQuestionTopic, Service, Resident,
                     Appointment, QueueTicket, Notification, TimeSlot,
                     BarangayAdminRegistration, BarangayStaff,
                     DocumentTemplate, GeneratedDocument)
from django.utils import timezone
from .forms import BarangayForm
from .services.admin_account_service import provision_admin_registration


class BarangayAdminRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    password1 = forms.CharField(
        label="Initial password",
        widget=forms.PasswordInput,
        required=False,
        help_text="Required when creating a registration. Leave blank when editing to keep the password.",
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
        required=False,
    )
    account_is_active = forms.BooleanField(
        label="Administrator account is active",
        required=False,
        initial=True,
    )

    class Meta:
        model = BarangayAdminRegistration
        fields = (
            "barangay", "municipality", "province", "complete_address", "zip_code",
            "contact_number", "email",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            # This form exists only inside the superuser-only Django Admin flow.
            self.instance.origin = BarangayAdminRegistration.Origin.SUPERUSER
        if self.instance.pk and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["username"].initial = self.instance.user.username
            self.fields["account_is_active"].initial = self.instance.user.is_active

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        users = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            users = users.exclude(pk=self.instance.user_id)
        if users.exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        users = User.objects.filter(email__iexact=email) if email else User.objects.none()
        if self.instance.pk:
            users = users.exclude(pk=self.instance.user_id)
        if users.exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
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
        barangay = cleaned_data.get("barangay")
        if barangay and barangay.user_id:
            current_user_id = self.instance.user_id if self.instance.pk else None
            if barangay.user_id != current_user_id:
                self.add_error("barangay", "This barangay already has an administrator account.")
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
    form = BarangayForm
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
    form = BarangayAdminRegistrationForm
    list_display = ("barangay", "user", "origin", "contact_number", "email", "status", "created_at")
    list_filter = ("origin", "status")
    search_fields = ("barangay__name", "user__username", "email", "contact_number")
    readonly_fields = ("origin", "status", "created_at", "terms_accepted_at", "reviewed_at")
    actions = ("approve_registrations", "reject_registrations")
    fieldsets = (
        ("Barangay", {"fields": (
            "barangay", "municipality", "province", "complete_address", "zip_code",
        )}),
        ("Administrator account", {"fields": (
            "first_name", "last_name", "username", "email", "contact_number",
            "password1", "password2", "account_is_active",
        )}),
        ("Registration audit", {"fields": (
            "origin", "terms_accepted_at", "status", "reviewed_at", "created_at",
        )}),
    )

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Keep the registration and approval audit trail intact."""
        return False

    @staticmethod
    def _provision(registration, *, is_active=True):
        provision_admin_registration(registration, is_active=is_active)

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            raise PermissionDenied
        if change:
            user = obj.user
            user.username = form.cleaned_data["username"]
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.email = obj.email
            if form.cleaned_data.get("password1"):
                user.set_password(form.cleaned_data["password1"])
            user.save()
        else:
            user = User(
                username=form.cleaned_data["username"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=obj.email,
                is_active=True,
                is_staff=False,
            )
            user.set_password(form.cleaned_data["password1"])
            user.save()
            obj.user = user
            obj.origin = BarangayAdminRegistration.Origin.SUPERUSER
            obj.terms_accepted_at = None
            obj.status = BarangayAdminRegistration.Status.APPROVED
            obj.reviewed_at = timezone.now()

        super().save_model(request, obj, form, change)
        if obj.status == BarangayAdminRegistration.Status.APPROVED:
            self._provision(obj, is_active=form.cleaned_data["account_is_active"])

    @admin.action(description="Approve selected barangay admin registrations")
    def approve_registrations(self, request, queryset):
        approved = 0
        for registration in queryset.select_related("user", "barangay"):
            if registration.status != BarangayAdminRegistration.Status.PENDING:
                continue
            if registration.barangay.user_id not in (None, registration.user_id):
                continue
            with transaction.atomic():
                self._provision(registration)
                registration.status = BarangayAdminRegistration.Status.APPROVED
                registration.reviewed_at = timezone.now()
                registration.save(update_fields=("status", "reviewed_at"))
                approved += 1
        self.message_user(request, f"Approved {approved} registration(s).")

    @admin.action(description="Reject selected barangay admin registrations")
    def reject_registrations(self, request, queryset):
        pending = queryset.filter(status=BarangayAdminRegistration.Status.PENDING)
        user_ids = list(pending.values_list("user_id", flat=True))
        rejected = pending.update(status=BarangayAdminRegistration.Status.REJECTED, reviewed_at=timezone.now())
        User.objects.filter(pk__in=user_ids).update(is_active=False)
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
