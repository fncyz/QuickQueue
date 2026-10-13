from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from qq.models import Barangay, BarangayAdminRegistration, BarangayStaff


class BarangayAdminCreationTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="root-admin",
            email="root@example.com",
            password="test-password",
        )
        self.client.force_login(self.superuser)
        self.existing = Barangay.objects.get(name="Poblacion")

    def test_superuser_creates_barangay_without_registration_record(self):
        response = self.client.post(
            reverse("admin:qq_barangay_add"),
            {
                "name": "Cambang-ug",
                "address": "Toledo City",
                "contact_number": "09987654321",
                "email": "bato@example.com",
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:qq_barangay_changelist"))
        barangay = Barangay.objects.get(name="Cambang-ug")
        self.assertIsNone(barangay.user)
        self.assertFalse(BarangayAdminRegistration.objects.filter(barangay=barangay).exists())
        self.assertTrue(Barangay.objects.filter(pk=self.existing.pk, name="Poblacion").exists())

    def test_admin_rejects_case_insensitive_duplicate_barangay_name(self):
        response = self.client.post(
            reverse("admin:qq_barangay_add"),
            {
                "name": "poblacion",
                "address": "Another address",
                "contact_number": "09111111111",
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A barangay with this name already exists.")
        self.assertEqual(Barangay.objects.filter(name__iexact="Poblacion").count(), 1)

    def test_registration_admin_does_not_offer_or_accept_additions(self):
        response = self.client.get(reverse("admin:qq_barangayadminregistration_add"))

        self.assertEqual(response.status_code, 403)

    def test_genuine_registration_still_records_terms_acceptance(self):
        self.client.logout()
        barangay = Barangay.objects.get(name="Luray 2")

        response = self.client.post(
            reverse("barangay_admin_registration"),
            {
                "barangay": barangay.pk,
                "municipality": "Toledo City",
                "province": "Cebu",
                "complete_address": "Barangay Hall, Luray 2",
                "zip_code": "6038",
                "username": "luray-registration",
                "contact_number": "09981234567",
                "email": "luray-registration@example.com",
                "password": "test-password",
                "confirm_password": "test-password",
                "terms": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        registration = BarangayAdminRegistration.objects.get(barangay=barangay)
        self.assertIsNotNone(registration.terms_accepted_at)
        self.assertEqual(registration.status, BarangayAdminRegistration.Status.PENDING)

    def test_barangay_admin_can_be_assigned_through_staff_admin(self):
        user = User.objects.create_user("bato-admin", password="test-password")
        barangay = Barangay.objects.create(
            name="Cambang-ug",
            address="Toledo City",
            contact_number="09987654321",
        )

        response = self.client.post(
            reverse("admin:qq_barangaystaff_add"),
            {
                "barangay": barangay.pk,
                "user": user.pk,
                "first_name": "Bato",
                "last_name": "Admin",
                "middle_name": "",
                "username": user.username,
                "email": "bato-admin@example.com",
                "contact_number": "09987654321",
                "role": BarangayStaff.Role.ADMIN,
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:qq_barangaystaff_changelist"))
        self.assertTrue(
            BarangayStaff.objects.filter(
                barangay=barangay,
                user=user,
                role=BarangayStaff.Role.ADMIN,
            ).exists()
        )
