from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from qq.models import Barangay, BarangayAdminRegistration, BarangayStaff, Resident


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

    def test_regular_staff_can_still_be_assigned_through_staff_admin(self):
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
                "role": BarangayStaff.Role.STAFF,
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:qq_barangaystaff_changelist"))
        self.assertTrue(
            BarangayStaff.objects.filter(
                barangay=barangay,
                user=user,
                role=BarangayStaff.Role.STAFF,
            ).exists()
        )


class BarangayAdministratorManagementTests(TestCase):
    password = "Secure-Admin-Password-482!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="system-owner",
            email="owner@example.com",
            password="superuser-password",
        )
        self.barangay = Barangay.objects.get(name="Poblacion")
        self.other_barangay = Barangay.objects.get(name="Bato")

    def _create_admin_through_django_admin(self):
        self.client.force_login(self.superuser)
        return self.client.post(
            reverse("admin:qq_barangayadministrator_add"),
            {
                "barangay": self.barangay.pk,
                "first_name": "Poblacion",
                "middle_name": "",
                "last_name": "Administrator",
                "username": "poblacion-managed-admin",
                "email": "managed-admin@example.com",
                "contact_number": "09981234567",
                "password1": self.password,
                "password2": self.password,
                "is_active": "on",
                "_save": "Save",
            },
        )

    def test_superuser_can_open_and_create_barangay_admin(self):
        self.client.force_login(self.superuser)
        self.assertEqual(
            self.client.get(reverse("admin:qq_barangayadministrator_changelist")).status_code,
            200,
        )

        response = self._create_admin_through_django_admin()

        self.assertRedirects(response, reverse("admin:qq_barangayadministrator_changelist"))
        profile = BarangayStaff.objects.select_related("user").get(
            username="poblacion-managed-admin"
        )
        self.assertEqual(profile.barangay, self.barangay)
        self.assertEqual(profile.role, BarangayStaff.Role.ADMIN)
        self.assertTrue(profile.is_active)
        self.assertTrue(profile.user.is_active)
        self.assertFalse(profile.user.is_staff)
        self.assertNotEqual(profile.user.password, self.password)
        self.assertTrue(profile.user.check_password(self.password))
        self.assertFalse(
            BarangayAdminRegistration.objects.filter(user=profile.user).exists()
        )

    def test_created_admin_logs_in_and_is_scoped_to_assigned_barangay(self):
        self._create_admin_through_django_admin()
        assigned_user = User.objects.create_user("assigned-resident", password="resident-password")
        other_user = User.objects.create_user("other-resident", password="resident-password")
        Resident.objects.create(
            user=assigned_user, first_name="Assigned", last_name="Resident",
            birthdate="1990-01-01", sex=Resident.Sex.FEMALE,
            email="assigned@example.com", contact_number="09170000001",
            barangay=self.barangay,
        )
        Resident.objects.create(
            user=other_user, first_name="Hidden", last_name="Resident",
            birthdate="1990-01-01", sex=Resident.Sex.MALE,
            email="hidden@example.com", contact_number="09170000002",
            barangay=self.other_barangay,
        )
        self.client.logout()

        login_response = self.client.post(
            reverse("signin"),
            {"username": "poblacion-managed-admin", "password": self.password},
        )

        self.assertRedirects(login_response, reverse("barangay_dashboard"))
        residents_response = self.client.get(reverse("barangay_residents"))
        self.assertEqual(residents_response.status_code, 200)
        self.assertEqual(residents_response.context["barangay"], self.barangay)
        visible_names = {resident.first_name for resident in residents_response.context["residents_page"]}
        self.assertIn("Assigned", visible_names)
        self.assertNotIn("Hidden", visible_names)

    def test_non_superuser_cannot_access_global_admin_management(self):
        user = User.objects.create_user(
            "ordinary-barangay-admin",
            password=self.password,
            is_staff=True,
        )
        BarangayStaff.objects.create(
            barangay=self.barangay,
            user=user,
            first_name="Ordinary",
            last_name="Admin",
            username=user.username,
            role=BarangayStaff.Role.ADMIN,
        )
        self.client.force_login(user)

        self.assertEqual(
            self.client.get(reverse("admin:qq_barangayadministrator_changelist")).status_code,
            403,
        )

    def test_superuser_can_edit_and_deactivate_account(self):
        self._create_admin_through_django_admin()
        profile = BarangayStaff.objects.get(username="poblacion-managed-admin")

        response = self.client.post(
            reverse("admin:qq_barangayadministrator_change", args=(profile.pk,)),
            {
                "barangay": self.other_barangay.pk,
                "first_name": "Updated",
                "middle_name": "",
                "last_name": "Administrator",
                "username": "updated-managed-admin",
                "email": "updated-admin@example.com",
                "contact_number": "09981234567",
                "password1": "",
                "password2": "",
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:qq_barangayadministrator_changelist"))
        profile.refresh_from_db()
        profile.user.refresh_from_db()
        self.assertEqual(profile.barangay, self.other_barangay)
        self.assertEqual(profile.user.username, "updated-managed-admin")
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.user.is_active)
        self.assertTrue(profile.user.check_password(self.password))

    def test_reassignment_detaches_conflicting_legacy_barangay_owner_link(self):
        user = User.objects.create_user("legacy-admin", password=self.password, is_staff=True)
        self.barangay.user = user
        self.barangay.save(update_fields=("user", "updated_at"))
        profile = BarangayStaff.objects.create(
            barangay=self.barangay,
            user=user,
            first_name="Legacy",
            last_name="Admin",
            username=user.username,
            role=BarangayStaff.Role.ADMIN,
        )
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("admin:qq_barangayadministrator_change", args=(profile.pk,)),
            {
                "barangay": self.other_barangay.pk,
                "first_name": "Legacy",
                "middle_name": "",
                "last_name": "Admin",
                "username": user.username,
                "email": "legacy@example.com",
                "contact_number": "09981234567",
                "password1": "",
                "password2": "",
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:qq_barangayadministrator_changelist"))
        self.barangay.refresh_from_db()
        profile.refresh_from_db()
        self.assertIsNone(self.barangay.user)
        self.assertEqual(profile.barangay, self.other_barangay)

    def test_generic_staff_admin_cannot_create_administrator_role(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("admin:qq_barangaystaff_add"),
            {
                "barangay": self.barangay.pk,
                "first_name": "Bypass",
                "last_name": "Attempt",
                "middle_name": "",
                "username": "bypass-attempt",
                "email": "",
                "contact_number": "",
                "role": BarangayStaff.Role.ADMIN,
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BarangayStaff.objects.filter(username="bypass-attempt").exists())
