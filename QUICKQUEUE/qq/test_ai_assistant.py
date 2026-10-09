from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from qq.gemini_service import GeminiUnavailable
from qq.models import Barangay, Resident


class AiAssistantApiTests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="AI Test Barangay", address="Toledo City", contact_number="09123456780"
        )
        self.user = User.objects.create_user(username="ai-resident", password="secret")
        Resident.objects.create(
            user=self.user,
            first_name="AI",
            last_name="Resident",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.MALE,
            contact_number="09170000999",
            barangay=self.barangay,
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("api_chat")

    @patch("qq.api.views.ask_gemini", return_value="Open the Book tab and choose a service.")
    def test_chat_returns_real_provider_response_shape(self, mocked_gemini):
        response = self.client.post(self.url, {"message": "How do I book?", "history": []}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Open the Book tab and choose a service.")
        self.assertEqual(response.data["source"], "QuickQueue records and AI guidance")
        mocked_gemini.assert_called_once()

    @patch("qq.api.views.ask_gemini")
    def test_chat_returns_classified_timeout(self, mocked_gemini):
        mocked_gemini.side_effect = GeminiUnavailable(
            "The AI request timed out.", code="ai_timeout", http_status=504
        )

        response = self.client.post(self.url, {"message": "What services are available?"}, format="json")

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.data["error_code"], "ai_timeout")
        self.assertTrue(response.data["retryable"])

    @patch("qq.api.views.ask_gemini")
    def test_chat_reports_missing_configuration_without_fake_reply(self, mocked_gemini):
        mocked_gemini.side_effect = GeminiUnavailable(
            "The AI service is not configured on the server.",
            code="ai_configuration",
            retryable=False,
        )

        response = self.client.post(self.url, {"message": "How do I check in?"}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error_code"], "ai_configuration")
        self.assertFalse(response.data["retryable"])
        self.assertNotIn("reply", response.data)
