from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from qq.gemini_service import GeminiUnavailable
from qq.models import Appointment, Barangay, Resident, Service, TimeSlot


class AiAssistantApiTests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="AI Test Barangay", address="Toledo City", contact_number="09123456780"
        )
        self.user = User.objects.create_user(username="ai-resident", password="secret")
        self.resident = Resident.objects.create(
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
        self.service = Service.objects.create(
            code="AIT", name="AI Test Service", description="Test", estimated_duration=15
        )
        self.slot = TimeSlot.objects.create(
            barangay=self.barangay, start_time=time(8), end_time=time(9), max_appointments=5
        )

    def _appointment(self, *, days=1, status=Appointment.Status.CONFIRMED, time_slot=True):
        return Appointment.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            service=self.service,
            appointment_date=date.today() + timedelta(days=days) if days is not None else None,
            time_slot=self.slot if time_slot else None,
            queue_number=f"A{Appointment.objects.count() + 1:02d}",
            status=status,
        )

    @patch("qq.api.views.ask_gemini", return_value="Open the Book tab and choose a service.")
    def test_chat_returns_real_provider_response_shape(self, mocked_gemini):
        response = self.client.post(self.url, {"message": "How do I book?", "history": []}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Open the Book tab and choose a service.")
        self.assertEqual(response.data["source"], "QuickQueue records and AI guidance")
        mocked_gemini.assert_called_once()

    @patch("qq.api.views.ask_gemini", return_value="Your appointment time is not assigned yet.")
    def test_chat_handles_active_appointment_without_time_slot(self, mocked_gemini):
        appointment = self._appointment(time_slot=False)

        response = self.client.post(self.url, {"message": "What time is my appointment?"}, format="json")

        self.assertEqual(response.status_code, 200)
        database_context = mocked_gemini.call_args.args[1]
        self.assertIn(f"ID QQ-{appointment.created_at.year}-{appointment.pk:05d}", database_context)
        self.assertIn("time=Time not assigned", database_context)

    @patch("qq.api.views.ask_gemini", return_value="Your appointment date and time are not assigned yet.")
    def test_chat_handles_active_appointment_without_date_or_time(self, mocked_gemini):
        self._appointment(days=None, time_slot=False, status=Appointment.Status.PENDING)

        response = self.client.post(self.url, {"message": "Show my appointment."}, format="json")

        self.assertEqual(response.status_code, 200)
        database_context = mocked_gemini.call_args.args[1]
        self.assertIn("date=Date not assigned", database_context)
        self.assertIn("time=Time not assigned", database_context)

    @patch("qq.api.views.ask_gemini", return_value="Your next active appointment is listed.")
    def test_chat_uses_earliest_upcoming_active_appointment(self, mocked_gemini):
        later = self._appointment(days=5)
        earlier = self._appointment(days=2)

        response = self.client.post(self.url, {"message": "What is my next appointment?"}, format="json")

        self.assertEqual(response.status_code, 200)
        database_context = mocked_gemini.call_args.args[1]
        self.assertIn(f"ID QQ-{earlier.created_at.year}-{earlier.pk:05d}", database_context)
        self.assertNotIn(f"ID QQ-{later.created_at.year}-{later.pk:05d}", database_context)

    @patch("qq.api.views.ask_gemini", return_value="You have no active upcoming appointment.")
    def test_cancelled_and_completed_appointments_are_not_reported_as_active(self, mocked_gemini):
        self._appointment(days=1, status=Appointment.Status.CANCELLED)
        self._appointment(days=-1, status=Appointment.Status.COMPLETED)

        response = self.client.post(self.url, {"message": "What is my appointment status?"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Active appointment: none", mocked_gemini.call_args.args[1])

    @patch("qq.api.views.ask_gemini")
    def test_chat_uses_verified_fallback_on_timeout(self, mocked_gemini):
        mocked_gemini.side_effect = GeminiUnavailable(
            "The AI request timed out.", code="ai_timeout", http_status=504
        )

        response = self.client.post(self.url, {"message": "What services are available?"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("AI Test Service", response.data["reply"])
        self.assertEqual(response.data["source"], "QuickQueue records and built-in guidance")
        self.assertTrue(response.data["fallback"])

    @patch("qq.api.views.ask_gemini")
    def test_chat_uses_verified_fallback_when_ai_is_not_configured(self, mocked_gemini):
        mocked_gemini.side_effect = GeminiUnavailable(
            "The AI service is not configured on the server.",
            code="ai_configuration",
            retryable=False,
        )

        response = self.client.post(self.url, {"message": "How do I check in?"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("don", response.data["reply"].lower())
        self.assertIn("appointments", response.data["reply"].lower())
        self.assertTrue(response.data["fallback"])

    @patch("qq.api.views.ask_gemini")
    def test_fallback_handles_unscheduled_appointment(self, mocked_gemini):
        self._appointment(days=None, time_slot=False, status=Appointment.Status.PENDING)
        mocked_gemini.side_effect = GeminiUnavailable("Provider unavailable")

        response = self.client.post(self.url, {"message": "How do I check in?"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("not been assigned", response.data["reply"])
        self.assertTrue(response.data["fallback"])
