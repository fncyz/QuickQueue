from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from qq.models import Barangay, BarangayStaff


class AdministrativeTemporaryPasswordTests(TestCase):
    super_password = "StrongPass1!"
    old_password = "OldStrong1!"
    temporary_password = "Temporary2!"
    final_password = "FinalStrong3!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="reset-superuser", email="super@example.com", password=self.super_password
        )
        self.barangay = Barangay.objects.create(
            name="Reset Barangay", address="Toledo City", contact_number="09123456789"
        )
        self.admin_user = User.objects.create_user(
            username="reset-admin", email="admin@example.com", password=self.old_password
        )
        self.profile = BarangayStaff.objects.create(
            user=self.admin_user, barangay=self.barangay,
            first_name="Reset", last_name="Admin", username="reset-admin",
            role=BarangayStaff.Role.ADMIN,
        )
        self.barangay.user = self.admin_user
        self.barangay.save(update_fields=["user"])
        self.super_client = Client()
        self.super_client.force_login(self.superuser)

    def reset_payload(self, **overrides):
        data = {
            "superuser_password": self.super_password,
            "temporary_password1": self.temporary_password,
            "temporary_password2": self.temporary_password,
        }
        data.update(overrides)
        return data

    def test_existing_profiles_default_to_no_forced_change(self):
        self.assertFalse(self.profile.must_change_password)

    def test_reset_requires_superuser_reauthentication_and_validation(self):
        url = reverse("superadmin_admin_temporary_password", args=[self.admin_user.pk])
        wrong = self.super_client.post(url, self.reset_payload(superuser_password="wrong"))
        mismatch = self.super_client.post(url, self.reset_payload(temporary_password2="Different3!"))
        weak = self.super_client.post(url, self.reset_payload(
            temporary_password1="123", temporary_password2="123"
        ))

        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(weak.status_code, 400)
        self.admin_user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertTrue(self.admin_user.check_password(self.old_password))
        self.assertFalse(self.profile.must_change_password)

    def test_reset_hashes_password_sets_flag_and_invalidates_sessions(self):
        admin_client = Client()
        self.assertTrue(admin_client.login(username=self.admin_user.username, password=self.old_password))
        old_session_key = admin_client.session.session_key

        response = self.super_client.post(
            reverse("superadmin_admin_temporary_password", args=[self.admin_user.pk]),
            self.reset_payload(),
        )

        self.assertRedirects(response, reverse("superadmin_admin_detail", args=[self.admin_user.pk]))
        self.admin_user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertTrue(self.admin_user.check_password(self.temporary_password))
        self.assertNotEqual(self.admin_user.password, self.temporary_password)
        self.assertTrue(self.profile.must_change_password)
        self.assertFalse(Session.objects.filter(session_key=old_session_key).exists())
        self.assertEqual(self.profile.role, BarangayStaff.Role.ADMIN)
        self.assertEqual(self.profile.barangay, self.barangay)

    def test_temporary_login_is_restricted_until_password_changes(self):
        self.super_client.post(
            reverse("superadmin_admin_temporary_password", args=[self.admin_user.pk]),
            self.reset_payload(),
        )
        admin_client = Client()
        login_response = admin_client.post(reverse("signin"), {
            "username": self.admin_user.username, "password": self.temporary_password,
        })
        self.assertRedirects(
            login_response, reverse("mandatory_password_change"), fetch_redirect_response=False
        )
        self.assertRedirects(
            admin_client.get(reverse("barangay_dashboard")),
            reverse("mandatory_password_change"), fetch_redirect_response=False,
        )
        api_response = admin_client.get("/api/profile/")
        self.assertEqual(api_response.status_code, 403)
        self.assertEqual(admin_client.get(reverse("mandatory_password_change")).status_code, 200)

        changed = admin_client.post(reverse("mandatory_password_change"), {
            "new_password1": self.final_password,
            "new_password2": self.final_password,
        })
        self.assertRedirects(changed, reverse("barangay_dashboard"), fetch_redirect_response=False)
        self.profile.refresh_from_db()
        self.admin_user.refresh_from_db()
        self.assertFalse(self.profile.must_change_password)
        self.assertTrue(self.admin_user.check_password(self.final_password))
        self.assertEqual(admin_client.get(reverse("barangay_dashboard")).status_code, 200)

    def test_regular_staff_is_not_affected(self):
        staff_user = User.objects.create_user(username="regular-staff", password=self.old_password)
        BarangayStaff.objects.create(
            user=staff_user, barangay=self.barangay, first_name="Regular", last_name="Staff",
            username="regular-staff", role=BarangayStaff.Role.STAFF,
        )
        client = Client()
        response = client.post(reverse("signin"), {
            "username": staff_user.username, "password": self.old_password,
        })
        self.assertRedirects(response, reverse("staff_dashboard"), fetch_redirect_response=False)
