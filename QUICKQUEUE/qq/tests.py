from django.contrib.auth.hashers import check_password
from rest_framework.test import APITestCase

from qq.models import Barangay, Resident


class RegistrationSecurityFlowTests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Test Barangay",
            address="Toledo City",
            contact_number="09123456789",
        )

    def test_registration_requires_password_then_pin_before_optional_biometrics(self):
        response = self.client.post("/api/register/", {
            "username": "newresident",
            "first_name": "New",
            "last_name": "Resident",
            "birthdate": "2000-01-01",
            "sex": "M",
            "contact_number": "09999999999",
            "barangay": self.barangay.pk,
            "terms_accepted": True,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("temporary_password", response.data)
        self.assertEqual(response.data["security_setup_stage"], "password")

        resident = Resident.objects.get(user__username="newresident")
        self.assertFalse(resident.user.has_usable_password())
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

        early_pin = self.client.post("/api/set-security-pin/", {"pin": "1234"}, format="json")
        self.assertEqual(early_pin.status_code, 409)

        password = self.client.post("/api/set-initial-password/", {
            "new_password": "StrongPass1!",
            "confirm_password": "StrongPass1!",
        }, format="json")
        self.assertEqual(password.status_code, 200)

        pin = self.client.post("/api/set-security-pin/", {"pin": "4826"}, format="json")
        self.assertEqual(pin.status_code, 200)
        resident.refresh_from_db()
        self.assertNotEqual(resident.pin_hash, "4826")
        self.assertTrue(check_password("4826", resident.pin_hash))
        self.assertEqual(resident.security_setup_stage, "fingerprint")

        for step, next_step in (("fingerprint", "face"), ("face", "complete")):
            advanced = self.client.post("/api/advance-security-setup/", {"step": step}, format="json")
            self.assertEqual(advanced.status_code, 200)
            self.assertEqual(advanced.data["next_step"], next_step)
