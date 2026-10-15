from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from qq.models import Barangay, BarangayAdminRegistration, BarangayStaff


class SuperAdminVerificationTests(TestCase):
    password = "StrongPass1!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="verification-superuser", email="super@example.com", password=self.password
        )
        self.client.force_login(self.superuser)
        self.barangay = Barangay.objects.create(
            name="Verification Barangay", address="Verification Address",
            contact_number="09112223333", email="barangay@example.com",
        )

    def application(self, username="applicant", status=BarangayAdminRegistration.Status.PENDING, barangay=None):
        user = User.objects.create_user(
            username=username, password=self.password,
            first_name="Pending", last_name="Applicant",
            email=f"{username}@example.com", is_active=False,
        )
        return BarangayAdminRegistration.objects.create(
            user=user, barangay=barangay or self.barangay,
            municipality="Toledo City", province="Cebu",
            complete_address="Applicant Address", zip_code="6038",
            contact_number="09998887777", email=user.email,
            terms_accepted_at=timezone.now(), status=status,
            reviewed_at=timezone.now() if status != BarangayAdminRegistration.Status.PENDING else None,
        )

    def test_list_defaults_to_pending_and_supports_search_filter_sort_pagination(self):
        target = self.application("target-applicant")
        self.application("approved-applicant", BarangayAdminRegistration.Status.APPROVED)
        for index in range(10):
            barangay = Barangay.objects.create(
                name=f"Verification Page {index}", address="Toledo City",
                contact_number=f"094{index:08d}"[-11:],
            )
            self.application(f"page-applicant-{index}", barangay=barangay)

        default_response = self.client.get(reverse("superadmin_pending_verifications"))
        search_response = self.client.get(reverse("superadmin_pending_verifications"), {
            "q": "target", "status": "all", "sort": "oldest",
        })
        page_two = self.client.get(reverse("superadmin_pending_verifications"), {"page": 2})

        self.assertEqual(default_response.context["status_filter"], "pending")
        self.assertNotContains(default_response, "approved-applicant")
        self.assertEqual(list(search_response.context["verification_page"]), [target])
        self.assertEqual(search_response.context["sort_order"], "oldest")
        self.assertEqual(page_two.context["verification_page"].number, 2)

    def test_superuser_can_review_and_approve_pending_application(self):
        application = self.application()
        detail = self.client.get(reverse("superadmin_verification_detail", args=[application.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, application.complete_address)

        response = self.client.post(reverse("superadmin_verification_approve", args=[application.pk]))
        self.assertRedirects(response, reverse("superadmin_verification_detail", args=[application.pk]))
        application.refresh_from_db()
        application.user.refresh_from_db()
        self.barangay.refresh_from_db()
        self.assertEqual(application.status, BarangayAdminRegistration.Status.APPROVED)
        self.assertIsNotNone(application.reviewed_at)
        self.assertTrue(application.user.is_active)
        self.assertFalse(application.user.is_staff)
        self.assertFalse(application.user.is_superuser)
        self.assertEqual(self.barangay.user, application.user)
        self.assertEqual(application.user.staff_profile.role, BarangayStaff.Role.ADMIN)

    def test_approval_rejects_occupied_barangay_without_partial_changes(self):
        existing = User.objects.create_user(username="existing-admin", password=self.password)
        self.barangay.user = existing
        self.barangay.save(update_fields=["user"])
        application = self.application()

        response = self.client.post(reverse("superadmin_verification_approve", args=[application.pk]), follow=True)

        application.refresh_from_db()
        application.user.refresh_from_db()
        self.assertEqual(application.status, BarangayAdminRegistration.Status.PENDING)
        self.assertFalse(application.user.is_active)
        self.assertEqual(self.barangay.user, existing)
        self.assertContains(response, "already has an administrator account")

    def test_superuser_can_reject_and_preserve_application(self):
        application = self.application()

        response = self.client.post(reverse("superadmin_verification_reject", args=[application.pk]))

        self.assertRedirects(response, reverse("superadmin_verification_detail", args=[application.pk]))
        application.refresh_from_db()
        self.assertEqual(application.status, BarangayAdminRegistration.Status.REJECTED)
        self.assertIsNotNone(application.reviewed_at)
        self.assertTrue(BarangayAdminRegistration.objects.filter(pk=application.pk).exists())

    def test_processed_application_cannot_be_processed_again(self):
        application = self.application(status=BarangayAdminRegistration.Status.REJECTED)
        response = self.client.post(
            reverse("superadmin_verification_approve", args=[application.pk]), follow=True
        )
        application.refresh_from_db()
        self.assertEqual(application.status, BarangayAdminRegistration.Status.REJECTED)
        self.assertContains(response, "already been processed")
        self.assertFalse(BarangayStaff.objects.filter(user=application.user).exists())

    def test_dashboard_updates_after_decision(self):
        application = self.application()
        before = self.client.get(reverse("superadmin_dashboard"))
        self.assertEqual(before.context["pending_applications"], 1)

        self.client.post(reverse("superadmin_verification_approve", args=[application.pk]))
        after = self.client.get(reverse("superadmin_dashboard"))

        self.assertEqual(after.context["pending_applications"], 0)
        self.assertEqual(after.context["approved_applications"], 1)
        self.assertEqual(len(after.context["pending_verifications"]), 0)
        self.assertEqual(after.context["recent_activities"][0]["kind"], "approved")

    def test_non_superuser_cannot_access_verification_routes(self):
        application = self.application()
        user = User.objects.create_user(username="blocked-verifier", password=self.password)
        self.client.force_login(user)
        endpoints = (
            ("get", reverse("superadmin_pending_verifications")),
            ("get", reverse("superadmin_verification_detail", args=[application.pk])),
            ("post", reverse("superadmin_verification_approve", args=[application.pk])),
            ("post", reverse("superadmin_verification_reject", args=[application.pk])),
        )
        for method, url in endpoints:
            with self.subTest(method=method, url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 403)
