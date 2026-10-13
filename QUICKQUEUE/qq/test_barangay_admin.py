from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from qq.models import Barangay, BarangayAdminRegistration, BarangayStaff, Resident


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
