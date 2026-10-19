from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from qq.models import Appointment, Barangay, BarangayAdminRegistration, BarangayStaff, DocumentTemplate, Resident, Service


class BarangayAdminRegistrationManagementTests(TestCase):
    password = "Secure-Admin-Password-482!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="system-owner", email="owner@example.com", password="superuser-password",
        )
        self.barangay = Barangay.objects.get(name="Poblacion")
        self.other_barangay = Barangay.objects.get(name="Bato")
        self.client.force_login(self.superuser)

    def _registration_data(self, **overrides):
        data = {
            "barangay": self.barangay.pk, "municipality": "Toledo City", "province": "Cebu",
            "complete_address": "Barangay Hall, Poblacion, Toledo City", "zip_code": "6038",
            "first_name": "Poblacion", "last_name": "Administrator",
            "username": "poblacion-managed-admin", "email": "managed-admin@example.com",
            "contact_number": "09981234567", "password1": self.password,
            "password2": self.password, "account_is_active": "on", "_save": "Save",
        }
        data.update(overrides)
        return data

    def _create_registration(self):
        return self.client.post(
            reverse("admin:qq_barangayadminregistration_add"), self._registration_data(),
        )

    def test_superuser_can_create_barangay_without_registration(self):
        response = self.client.post(reverse("admin:qq_barangay_add"), {
            "name": "Cambang-ug", "address": "Toledo City", "contact_number": "09987654321",
            "email": "cambangug@example.com", "is_active": "on", "_save": "Save",
        })
        self.assertRedirects(response, reverse("admin:qq_barangay_changelist"))
        barangay = Barangay.objects.get(name="Cambang-ug")
        self.assertFalse(BarangayAdminRegistration.objects.filter(barangay=barangay).exists())
        self.assertTrue(Barangay.objects.filter(pk=self.barangay.pk, name="Poblacion").exists())

    def test_admin_template_header_is_clean_and_upload_trigger_is_preserved(self):
        self.barangay.user = self.superuser
        self.barangay.save(update_fields=["user", "updated_at"])

        templates_page = self.client.get(reverse("barangay_document_templates"))

        self.assertEqual(templates_page.status_code, 200)
        self.assertContains(templates_page, "Document Templates")
        self.assertContains(
            templates_page,
            "Upload and manage the source document for each barangay service.",
        )
        self.assertContains(templates_page, 'id="open-upload"', count=1)
        self.assertContains(templates_page, 'id="template-search"', count=1)
        self.assertContains(templates_page, 'placeholder="Search document templates..."')
        self.assertContains(templates_page, 'class="template-grid"')
        self.assertContains(templates_page, "qq/js/document_templates.js")
        self.assertContains(templates_page, 'type="button" class="close secondary">Cancel</button>')
        self.assertContains(
            templates_page,
            "#template-dialog footer .secondary{width:auto;height:42px",
        )
        self.assertContains(templates_page, "font:700 14px Poppins,sans-serif")
        self.assertNotContains(templates_page, "<table")
        self.assertNotContains(templates_page, "Service document library")
        self.assertNotContains(templates_page, "template-intro")
        self.assertNotContains(templates_page, "alert-bell")
        self.assertNotContains(templates_page, "qq-notification-root")

        dashboard = self.client.get(reverse("barangay_dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertNotContains(dashboard, "alert-bell")
        self.assertNotContains(dashboard, "qq-notification-root")

    @override_settings(
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        },
        MEDIA_URL="/media/",
    )
    def test_document_template_api_returns_safe_card_metadata_for_assigned_barangay(self):
        self.barangay.user = self.superuser
        self.barangay.save(update_fields=["user", "updated_at"])
        service = Service.objects.filter(is_temporary=False).first()
        own_template = DocumentTemplate.objects.create(
            barangay=self.barangay,
            service=service,
            name="Poblacion Clearance Template",
            template_file="document_templates/poblacion-clearance.pdf",
        )
        DocumentTemplate.objects.create(
            barangay=self.other_barangay,
            service=service,
            name="Private Bato Template",
            template_file="document_templates/private-bato.docx",
        )

        response = self.client.get(reverse("api_document_templates"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], own_template.pk)
        self.assertEqual(payload[0]["file_name"], "poblacion-clearance.pdf")
        self.assertEqual(payload[0]["file_type"], "PDF")
        self.assertEqual(payload[0]["service_name"], service.name)
        self.assertNotContains(response, "Private Bato Template")

    def test_admin_dashboard_special_services_are_scoped_current_and_read_only(self):
        self.barangay.user = self.superuser
        self.barangay.save(update_fields=["user", "updated_at"])
        today = timezone.localdate()
        active = Service.objects.create(
            code="EVT9",
            name="Phase 9 Community Event",
            description="Dashboard visibility test",
            estimated_duration=15,
            is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT,
            barangay=self.barangay,
            location="Poblacion Covered Court",
            event_start_date=today,
            event_end_date=today,
            booking_start_date=today,
            booking_end_date=today,
            capacity=10,
        )
        Service.objects.create(
            code="OTH9",
            name="Other Barangay Event",
            description="Must remain isolated",
            estimated_duration=15,
            is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT,
            barangay=self.other_barangay,
            location="Other Hall",
            event_start_date=today,
            event_end_date=today,
            booking_start_date=today,
            booking_end_date=today,
            capacity=20,
        )
        Service.objects.create(
            code="OLD9",
            name="Expired Barangay Event",
            description="Must remain historical",
            estimated_duration=15,
            is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT,
            barangay=self.barangay,
            event_start_date=today - timedelta(days=2),
            event_end_date=today - timedelta(days=1),
            booking_start_date=today - timedelta(days=5),
            booking_end_date=today - timedelta(days=1),
            capacity=10,
        )
        resident_user = User.objects.create_user("phase9-resident", password="secret")
        resident = Resident.objects.create(
            user=resident_user,
            first_name="Phase",
            last_name="Nine",
            birthdate="1990-01-01",
            sex=Resident.Sex.FEMALE,
            contact_number="09179999999",
            barangay=self.barangay,
        )
        Appointment.objects.create(
            resident=resident,
            barangay=self.barangay,
            service=active,
            appointment_date=today,
            status=Appointment.Status.CONFIRMED,
        )

        response = self.client.get(reverse("barangay_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item.pk for item in response.context["special_services"]], [active.pk])
        self.assertEqual(response.context["special_services"][0].dashboard_booking_count, 1)
        self.assertEqual(response.context["special_services"][0].remaining_capacity, 9)
        self.assertEqual(response.context["today_total"], 0)
        self.assertEqual(response.context["month_total"], 0)
        self.assertContains(response, "Phase 9 Community Event")
        self.assertContains(response, "Poblacion Covered Court")
        self.assertContains(response, "9</b> of 10 slots available")
        self.assertNotContains(response, "Other Barangay Event")
        self.assertNotContains(response, "Expired Barangay Event")
        self.assertNotContains(response, "Create Event")
        self.assertNotContains(response, "Edit Event")
        self.assertNotContains(response, "QR Scanner")

        active.is_active = False
        active.save(update_fields=["is_active", "updated_at"])
        empty_response = self.client.get(reverse("barangay_dashboard"))
        self.assertContains(empty_response, "No special services available.")

    def test_registration_admin_creates_approved_hashed_account_without_terms(self):
        response = self._create_registration()
        self.assertRedirects(response, reverse("admin:qq_barangayadminregistration_changelist"))
        registration = BarangayAdminRegistration.objects.select_related("user", "barangay").get(
            user__username="poblacion-managed-admin"
        )
        self.assertEqual(registration.origin, BarangayAdminRegistration.Origin.SUPERUSER)
        self.assertEqual(registration.status, BarangayAdminRegistration.Status.APPROVED)
        self.assertIsNone(registration.terms_accepted_at)
        self.assertIsNotNone(registration.reviewed_at)
        self.assertNotEqual(registration.user.password, self.password)
        self.assertTrue(registration.user.check_password(self.password))
        self.assertTrue(registration.user.is_active)
        self.assertFalse(registration.user.is_staff)
        self.assertEqual(registration.barangay.user, registration.user)
        self.assertTrue(BarangayStaff.objects.filter(
            user=registration.user, barangay=self.barangay,
            role=BarangayStaff.Role.ADMIN, is_active=True,
        ).exists())

    def test_created_administrator_logs_in_and_sees_only_assigned_barangay(self):
        self._create_registration()
        assigned_user = User.objects.create_user("assigned-resident", password="resident-password")
        hidden_user = User.objects.create_user("hidden-resident", password="resident-password")
        Resident.objects.create(
            user=assigned_user, first_name="Assigned", last_name="Resident", birthdate="1990-01-01",
            sex=Resident.Sex.FEMALE, email="assigned@example.com", contact_number="09170000001",
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=hidden_user, first_name="Hidden", last_name="Resident", birthdate="1990-01-01",
            sex=Resident.Sex.MALE, email="hidden@example.com", contact_number="09170000002",
            barangay=self.other_barangay,
        )
        self.client.logout()
        response = self.client.post(reverse("signin"), {
            "username": "poblacion-managed-admin", "password": self.password,
        })
        self.assertRedirects(response, reverse("barangay_dashboard"))
        residents = self.client.get(reverse("barangay_residents"))
        self.assertEqual(residents.context["barangay"], self.barangay)
        visible = {item.first_name for item in residents.context["residents_page"]}
        self.assertIn("Assigned", visible)
        self.assertNotIn("Hidden", visible)

    def test_duplicate_username_and_email_are_rejected(self):
        self._create_registration()
        response = self.client.post(
            reverse("admin:qq_barangayadminregistration_add"),
            self._registration_data(
                barangay=self.other_barangay.pk, username="POBLACION-MANAGED-ADMIN",
                email="MANAGED-ADMIN@EXAMPLE.COM",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with this username already exists.")
        self.assertContains(response, "A user with this email address already exists.")
        self.assertEqual(User.objects.filter(username__iexact="poblacion-managed-admin").count(), 1)

    def test_superuser_can_deactivate_account_by_editing_registration(self):
        self._create_registration()
        registration = BarangayAdminRegistration.objects.get(user__username="poblacion-managed-admin")
        response = self.client.post(
            reverse("admin:qq_barangayadminregistration_change", args=(registration.pk,)),
            self._registration_data(password1="", password2="", account_is_active=""),
        )
        self.assertRedirects(response, reverse("admin:qq_barangayadminregistration_changelist"))
        registration.user.refresh_from_db()
        staff = BarangayStaff.objects.get(user=registration.user)
        self.assertFalse(registration.user.is_active)
        self.assertFalse(staff.is_active)
        self.assertTrue(registration.user.check_password(self.password))

    def test_non_superuser_cannot_manage_registrations(self):
        user = User.objects.create_user("ordinary-staff", password=self.password, is_staff=True)
        self.client.force_login(user)
        self.assertEqual(
            self.client.get(reverse("admin:qq_barangayadminregistration_changelist")).status_code, 403,
        )
        self.assertEqual(
            self.client.get(reverse("admin:qq_barangayadminregistration_add")).status_code, 403,
        )

    def test_legacy_public_origin_still_requires_real_terms_acceptance(self):
        user = User.objects.create_user("legacy-request", email="legacy@example.com")
        registration = BarangayAdminRegistration(
            user=user, barangay=self.other_barangay, municipality="Toledo City", province="Cebu",
            complete_address="Barangay Hall, Bato", zip_code="6038", contact_number="09980000000",
            email="legacy@example.com", origin=BarangayAdminRegistration.Origin.LEGACY_PUBLIC,
        )
        with self.assertRaises(ValidationError):
            registration.full_clean()
        registration.terms_accepted_at = timezone.now()
        registration.full_clean()

    def test_no_separate_barangay_administrator_model_is_registered(self):
        registered_model_names = {model.__name__ for model in admin.site._registry}
        self.assertNotIn("BarangayAdministrator", registered_model_names)
