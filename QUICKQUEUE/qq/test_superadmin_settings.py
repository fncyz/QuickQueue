from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from qq.models import Barangay, BarangayStaff, Resident


class SuperAdminSettingsTests(TestCase):
    password = "StrongPass1!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="settings-superuser",
            password=self.password,
            email="settings@example.com",
            first_name="System",
            last_name="Administrator",
        )
        self.client.force_login(self.superuser)

    def test_superuser_can_view_safe_profile_system_and_security_information(self):
        response = self.client.get(reverse("superadmin_system_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Administrator")
        self.assertContains(response, "settings-superuser")
        self.assertContains(response, "System Administrator")
        self.assertContains(response, "PostgreSQL (Supabase)")
        self.assertContains(response, "Vercel")
        self.assertContains(response, "Asia/Manila")
        self.assertContains(response, "Password Policy")
        self.assertContains(response, "settings.css")
        self.assertNotContains(response, "SECRET_KEY")
        self.assertNotContains(response, "DATABASE_URL")
        self.assertTemplateUsed(response, "superadmin/components/sidebar.html")

    def test_account_security_uses_lucide_icons_and_accessible_password_toggles(self):
        response = self.client.get(reverse("superadmin_system_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'M4 21a8 8 0 0 1 16 0')
        self.assertContains(response, 'M7 11V7a5 5 0 0 1 10 0v4M12 15v2')
        self.assertContains(response, 'M22 3l-8.646 8.646')
        self.assertNotContains(response, '<header><i>#</i><span><h2>System Overview</h2>')
        self.assertContains(response, 'data-password-toggle aria-label="Show password"', count=3)
        self.assertContains(response, 'aria-label="Show password" aria-pressed="false"', count=3)
        self.assertContains(response, 'class="eye-off"', count=3)
        self.assertContains(response, 'class="eye"', count=3)
        self.assertNotContains(response, '>Show</button>')

    def test_profile_update_changes_only_allowed_user_fields(self):
        response = self.client.post(reverse("superadmin_system_settings"), {
            "action": "profile",
            "first_name": "Updated",
            "last_name": "Super Admin",
            "email": "updated-super@example.com",
        })

        self.assertRedirects(response, reverse("superadmin_system_settings"))
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.first_name, "Updated")
        self.assertEqual(self.superuser.last_name, "Super Admin")
        self.assertEqual(self.superuser.email, "updated-super@example.com")
        self.assertEqual(self.superuser.username, "settings-superuser")
        self.assertTrue(self.superuser.is_superuser)

    def test_profile_rejects_invalid_and_conflicting_email(self):
        User.objects.create_user(username="email-owner", email="owned@example.com")
        for email in ("invalid-email", "OWNED@example.com"):
            with self.subTest(email=email):
                response = self.client.post(reverse("superadmin_system_settings"), {
                    "action": "profile", "first_name": "System",
                    "last_name": "Administrator", "email": email,
                })
                self.assertEqual(response.status_code, 400)
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.email, "settings@example.com")

    def test_password_change_rejects_wrong_current_mismatch_and_weak_password(self):
        attempts = (
            {"old_password": "wrong", "new_password1": "NewStrong2!", "new_password2": "NewStrong2!"},
            {"old_password": self.password, "new_password1": "NewStrong2!", "new_password2": "Different2!"},
            {"old_password": self.password, "new_password1": "123", "new_password2": "123"},
        )
        for payload in attempts:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("superadmin_system_settings"), {"action": "password", **payload}
                )
                self.assertEqual(response.status_code, 400)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.check_password(self.password))

    def test_password_change_hashes_password_and_preserves_session(self):
        new_password = "NewStrong2!"
        response = self.client.post(reverse("superadmin_system_settings"), {
            "action": "password", "old_password": self.password,
            "new_password1": new_password, "new_password2": new_password,
        })

        self.assertRedirects(response, reverse("superadmin_system_settings"))
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.check_password(new_password))
        self.assertNotEqual(self.superuser.password, new_password)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.superuser.pk)
        self.assertEqual(self.client.get(reverse("superadmin_system_settings")).status_code, 200)

    def test_system_overview_uses_database_records_and_deduplicates_admins(self):
        barangay = Barangay.objects.create(
            name="Settings Barangay", address="Toledo City", contact_number="09123456789"
        )
        admin = User.objects.create_user(username="settings-admin", password=self.password)
        barangay.user = admin
        barangay.save(update_fields=["user"])
        BarangayStaff.objects.create(
            user=admin, barangay=barangay, first_name="Settings", last_name="Admin",
            username=admin.username, role=BarangayStaff.Role.ADMIN,
        )
        resident_user = User.objects.create_user(username="settings-resident", password=self.password)
        Resident.objects.create(
            user=resident_user, first_name="Settings", last_name="Resident",
            birthdate="2000-01-01", sex=Resident.Sex.MALE,
            contact_number="09999999999", barangay=barangay,
        )

        response = self.client.get(reverse("superadmin_system_settings"))

        self.assertEqual(response.context["overview"]["admins"], 1)
        self.assertEqual(response.context["overview"]["residents"], 1)
        self.assertEqual(response.context["overview"]["appointments"], 0)
        self.assertEqual(response.context["overview"]["barangays"], Barangay.objects.count())

    def test_non_superuser_cannot_access_or_update_settings(self):
        user = User.objects.create_user(username="blocked-settings", password=self.password)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("superadmin_system_settings")).status_code, 403)
        self.assertEqual(self.client.post(reverse("superadmin_system_settings"), {
            "action": "profile", "first_name": "Bad", "last_name": "Actor",
            "email": "bad@example.com",
        }).status_code, 403)
