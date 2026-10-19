from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from qq.models import Barangay, BarangayAdminRegistration, BarangayStaff


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SuperAdminAccountManagementTests(TestCase):
    password = "StrongPass1!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="account-superuser", email="super@example.com", password=self.password
        )
        self.client.force_login(self.superuser)
        self.barangay = Barangay.objects.create(
            name="Admin Account Barangay", address="Toledo City",
            contact_number="09110000000", email="barangay@example.com",
        )
        self.other_barangay = Barangay.objects.create(
            name="Other Admin Barangay", address="Toledo City",
            contact_number="09220000000", email="other@example.com",
        )

    def payload(self, **overrides):
        data = {
            "first_name": "Maria", "last_name": "Santos",
            "username": "maria-admin", "email": "maria@example.com",
            "barangay": str(self.barangay.pk),
            "password1": self.password, "password2": self.password,
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def create_admin(self):
        response = self.client.post(reverse("superadmin_admin_add"), self.payload())
        self.assertRedirects(response, reverse("superadmin_barangay_admins"))
        return User.objects.get(username="maria-admin")

    def test_registers_hashed_non_privileged_admin_with_existing_relationships(self):
        admin_user = self.create_admin()

        self.assertNotEqual(admin_user.password, self.password)
        self.assertTrue(admin_user.check_password(self.password))
        self.assertFalse(admin_user.is_superuser)
        self.assertFalse(admin_user.is_staff)
        self.assertEqual(admin_user.barangay_profile, self.barangay)
        self.assertEqual(admin_user.staff_profile.role, BarangayStaff.Role.ADMIN)
        self.assertEqual(admin_user.staff_profile.barangay, self.barangay)
        self.assertTrue(admin_user.staff_profile.must_change_password)
        registration = admin_user.barangay_admin_registration
        self.assertEqual(registration.status, BarangayAdminRegistration.Status.APPROVED)
        self.assertEqual(registration.origin, BarangayAdminRegistration.Origin.SUPERUSER)

        self.client.logout()
        login_response = self.client.post(reverse("signin"), {
            "username": admin_user.username, "password": self.password,
        })
        self.assertRedirects(
            login_response,
            reverse("mandatory_password_change"),
            fetch_redirect_response=False,
        )

    def test_duplicate_username_and_barangay_assignment_are_rejected(self):
        self.create_admin()
        duplicate_username = self.client.post(
            reverse("superadmin_admin_add"),
            self.payload(email="different@example.com", barangay=str(self.other_barangay.pk)),
        )
        occupied_barangay = self.client.post(
            reverse("superadmin_admin_add"),
            self.payload(username="different-admin", email="different@example.com"),
        )

        self.assertEqual(duplicate_username.status_code, 400)
        self.assertContains(duplicate_username, "A user with this username already exists.", status_code=400)
        self.assertEqual(occupied_barangay.status_code, 400)
        self.assertEqual(_admin_users().count(), 1)

    def test_edit_reassigns_only_account_relationships(self):
        admin_user = self.create_admin()
        response = self.client.post(reverse("superadmin_admin_edit", args=[admin_user.pk]), {
            "first_name": "Updated", "last_name": "Administrator",
            "email": "updated@example.com", "barangay": self.other_barangay.pk,
            "is_active": "on",
        })

        self.assertRedirects(
            response,
            f"{reverse('superadmin_barangay_admins')}?selected={admin_user.pk}",
        )
        admin_user.refresh_from_db()
        self.barangay.refresh_from_db()
        self.other_barangay.refresh_from_db()
        admin_user.staff_profile.refresh_from_db()
        self.assertIsNone(self.barangay.user_id)
        self.assertEqual(self.other_barangay.user_id, admin_user.pk)
        self.assertEqual(admin_user.staff_profile.barangay, self.other_barangay)
        self.assertEqual(admin_user.email, "updated@example.com")

    def test_admin_edit_preserves_safe_management_return_location(self):
        admin_user = self.create_admin()
        return_to = (
            f"{reverse('superadmin_barangay_admins')}?q=Maria&status=active"
            f"&sort=desc&page=1&selected={admin_user.pk}"
        )

        response = self.client.get(
            reverse("superadmin_admin_edit", args=[admin_user.pk]),
            {"return_to": return_to},
        )

        self.assertNotContains(response, "Back to Barangay Admins")
        self.assertContains(response, ">Cancel</button>")
        self.assertContains(response, "You have unsaved changes")
        self.assertContains(response, 'id="admin-modal" class="barangay-modal" open')
        self.assertContains(response, "removeAttribute('open');modal.showModal()")
        self.assertContains(response, "modal.addEventListener('cancel'")
        self.assertEqual(response.context["return_url"], return_to)

    def test_activation_controls_user_and_admin_profile(self):
        admin_user = self.create_admin()
        response = self.client.post(
            reverse("superadmin_admin_status", args=[admin_user.pk]), {"status": "inactive"}
        )
        self.assertRedirects(response, reverse("superadmin_admin_detail", args=[admin_user.pk]))
        admin_user.refresh_from_db()
        admin_user.staff_profile.refresh_from_db()
        self.assertFalse(admin_user.is_active)
        self.assertFalse(admin_user.staff_profile.is_active)
        self.client.logout()
        self.assertFalse(self.client.login(username=admin_user.username, password=self.password))

    def test_listing_deduplicates_and_supports_search_filters_and_pagination(self):
        admin_user = self.create_admin()
        response = self.client.get(reverse("superadmin_barangay_admins"), {
            "q": "Maria", "status": "active", "barangay": self.barangay.pk,
        })
        ids = [item.pk for item in response.context["admin_page"]]
        self.assertEqual(ids.count(admin_user.pk), 1)
        self.assertContains(response, "maria-admin")

        for index in range(10):
            barangay = Barangay.objects.create(
                name=f"Paged Admin Barangay {index}", address="Toledo City",
                contact_number=f"093{index:08d}"[-11:],
            )
            user = User.objects.create_user(
                username=f"paged-admin-{index}", password=self.password,
                first_name=f"Paged {index}", is_active=True,
            )
            barangay.user = user
            barangay.save(update_fields=["user"])
        page_two = self.client.get(reverse("superadmin_barangay_admins"), {"page": 2})
        self.assertEqual(page_two.context["admin_page"].number, 2)

    def test_administrator_details_panel_is_hidden_until_view_is_selected(self):
        admin_user = self.create_admin()

        default_response = self.client.get(reverse("superadmin_barangay_admins"))
        self.assertIsNone(default_response.context["selected_admin"])
        self.assertContains(
            default_response,
            'id="admin-selection" aria-label="Selected administrator details" hidden',
        )

        selected_response = self.client.get(
            reverse("superadmin_barangay_admins"), {"selected": admin_user.pk}
        )
        self.assertEqual(selected_response.context["selected_admin"], admin_user)
        self.assertContains(selected_response, "split-management panel-open")
        self.assertContains(selected_response, "Close selected administrator details")
        self.assertContains(selected_response, admin_user.email)

    def test_secure_password_reset_sends_token_link(self):
        admin_user = self.create_admin()
        response = self.client.post(reverse("superadmin_admin_password_reset", args=[admin_user.pk]))

        self.assertRedirects(response, reverse("superadmin_admin_detail", args=[admin_user.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reset/", mail.outbox[0].body)
        self.assertNotIn(self.password, mail.outbox[0].body)

    def test_non_superuser_cannot_access_management_endpoints(self):
        admin_user = self.create_admin()
        ordinary = User.objects.create_user(username="blocked-user", password=self.password)
        self.client.force_login(ordinary)
        endpoints = (
            ("get", reverse("superadmin_barangay_admins"), {}),
            ("get", reverse("superadmin_admin_detail", args=[admin_user.pk]), {}),
            ("get", reverse("superadmin_admin_edit", args=[admin_user.pk]), {}),
            ("post", reverse("superadmin_admin_add"), {}),
            ("post", reverse("superadmin_admin_edit", args=[admin_user.pk]), {}),
            ("post", reverse("superadmin_admin_status", args=[admin_user.pk]), {"status": "inactive"}),
            ("post", reverse("superadmin_admin_password_reset", args=[admin_user.pk]), {}),
        )
        for method, url, data in endpoints:
            with self.subTest(method=method, url=url):
                self.assertEqual(getattr(self.client, method)(url, data).status_code, 403)


def _admin_users():
    return User.objects.filter(
        barangay_profile__isnull=False,
        is_superuser=False,
    )
