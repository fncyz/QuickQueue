from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from qq.models import Barangay, BarangayAdminRegistration


class RetiredSuperAdminVerificationInterfaceTests(TestCase):
    password = "StrongPass1!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="system-administrator",
            email="system@example.com",
            password=self.password,
        )
        self.client.force_login(self.superuser)
        self.barangay = Barangay.objects.create(
            name="Historical Verification Barangay",
            address="Toledo City",
            contact_number="09112223333",
        )
        applicant = User.objects.create_user(
            username="historical-applicant",
            password=self.password,
            is_active=False,
        )
        self.registration = BarangayAdminRegistration.objects.create(
            user=applicant,
            barangay=self.barangay,
            municipality="Toledo City",
            province="Cebu",
            complete_address="Historical address",
            zip_code="6038",
            contact_number="09998887777",
            email="historical@example.com",
            terms_accepted_at=timezone.now(),
            status=BarangayAdminRegistration.Status.PENDING,
        )

    def test_retired_verification_routes_are_not_accessible(self):
        paths = (
            "/superadmin/pending-verifications/",
            f"/superadmin/pending-verifications/{self.registration.pk}/",
            f"/superadmin/pending-verifications/{self.registration.pk}/approve/",
            f"/superadmin/pending-verifications/{self.registration.pk}/reject/",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_historical_registration_is_preserved(self):
        before = BarangayAdminRegistration.objects.count()

        response = self.client.get(reverse("superadmin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BarangayAdminRegistration.objects.count(), before)
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, BarangayAdminRegistration.Status.PENDING)
        activity_types = {
            activity["activity_type"] for activity in response.context["recent_activities"]
        }
        self.assertIn("administrator_application_submitted", activity_types)
        self.assertContains(response, "activity-icon administrator_application_submitted")

    def test_reviewed_historical_registrations_use_explicit_activity_types(self):
        self.registration.status = BarangayAdminRegistration.Status.APPROVED
        self.registration.reviewed_at = timezone.now()
        self.registration.save(update_fields=("status", "reviewed_at"))

        response = self.client.get(reverse("superadmin_dashboard"))

        activity_types = {
            activity["activity_type"] for activity in response.context["recent_activities"]
        }
        self.assertIn("administrator_approved", activity_types)
        self.assertContains(response, "activity-icon administrator_approved")

    def test_verification_navigation_and_dashboard_ui_are_removed(self):
        response = self.client.get(reverse("superadmin_dashboard"))

        self.assertNotContains(response, "Pending Verifications")
        self.assertNotContains(response, "Verification Report")
        self.assertNotContains(response, "Administrator Applications")
        self.assertContains(response, "System Administrator Portal")
