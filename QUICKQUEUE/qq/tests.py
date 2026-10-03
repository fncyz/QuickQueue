from datetime import date, time
from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from qq.models import (
    Appointment,
    Barangay,
    DocumentTemplate,
    GeneratedDocument,
    Notification,
    QueueTicket,
    Resident,
    Service,
    TimeSlot,
)


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


class ResidentAppointmentApiTests(APITestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Appointment Test Barangay",
            address="Toledo City",
            contact_number="09111111111",
        )
        self.user = User.objects.create_user(username="appointment-resident", password="secret")
        self.resident = Resident.objects.create(
            user=self.user,
            first_name="Appointment",
            last_name="Resident",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.MALE,
            contact_number="09222222222",
            barangay=self.barangay,
        )
        self.service = Service.objects.create(
            code="DOC",
            name="Appointment Test Service",
            description="Test service",
            estimated_duration=15,
        )
        self.time_slot = TimeSlot.objects.create(
            barangay=self.barangay,
            start_time=time(9, 0),
            end_time=time(10, 0),
            max_appointments=5,
        )
        self.client.force_authenticate(user=self.user)

    def test_booking_returns_database_and_display_ids_and_creates_once(self):
        payload = {
            "service": self.service.pk,
            "time_slot": self.time_slot.pk,
            "appointment_date": date.today().isoformat(),
            "purpose": "API contract test",
            "sitio": "Test Sitio",
        }

        response = self.client.post("/api/appointments/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["id"], int)
        self.assertEqual(response.data["appointment_id"], f"QQ-{date.today().year}-{response.data['id']:05d}")
        self.assertEqual(Appointment.objects.filter(resident=self.resident).count(), 1)

        duplicate = self.client.post("/api/appointments/", payload, format="json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Appointment.objects.filter(resident=self.resident).count(), 1)

    def test_mobile_summary_and_notification_pagination_contracts(self):
        appointment = Appointment.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            service=self.service,
            appointment_date=date.today(),
            time_slot=self.time_slot,
            queue_number="DOC-004",
        )
        for index in range(3):
            Notification.objects.create(
                resident=self.resident,
                appointment=appointment,
                notification_type=Notification.NotificationType.QUEUE_UPDATE,
                title=f"Update {index}",
                message="Queue changed.",
            )

        profile = self.client.get("/api/profile/?summary=1")
        appointments = self.client.get("/api/appointments/?summary=1")
        notifications = self.client.get("/api/notifications/?summary=1")
        first_page = self.client.get("/api/notifications/?page=1&page_size=2")

        self.assertEqual(profile.data, {"username": self.user.username, "first_name": self.resident.first_name})
        self.assertIn({"id": self.service.pk, "name": self.service.name}, appointments.data["services"])
        self.assertEqual(notifications.data, {"unread_count": 3})
        self.assertEqual(len(first_page.data["notifications"]), 2)
        self.assertTrue(first_page.data["pagination"]["has_more"])
        self.assertEqual(first_page.data["pagination"]["total"], 3)

    def test_transaction_cancel_then_delete_uses_database_id(self):
        appointment = Appointment.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            service=self.service,
            appointment_date=date.today(),
            time_slot=self.time_slot,
            purpose="Action contract test",
            queue_number="DOC-001",
        )
        ticket = QueueTicket.objects.create(appointment=appointment, queue_number=appointment.queue_number)
        Notification.objects.create(
            resident=self.resident,
            appointment=appointment,
            notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
            title="Appointment Submitted",
            message="Full relation graph test",
        )
        template = DocumentTemplate.objects.create(
            barangay=self.barangay,
            service=self.service,
            name="Test Template",
            template_file="document_templates/test.docx",
        )
        GeneratedDocument.objects.create(
            ticket=ticket,
            template=template,
            document_file="generated_documents/test.pdf",
        )

        cancel = self.client.post(
            "/api/transactions/",
            {"appointment_id": appointment.pk, "action": "cancel"},
            format="json",
        )
        self.assertEqual(cancel.status_code, 200)
        self.assertTrue(cancel.data["success"])
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)

        delete = self.client.post(
            "/api/transactions/",
            {"appointment_id": appointment.pk, "action": "delete"},
            format="json",
        )
        self.assertEqual(delete.status_code, 200)
        self.assertTrue(delete.data["success"])
        self.assertFalse(Appointment.objects.filter(pk=appointment.pk).exists())
        self.assertFalse(QueueTicket.objects.filter(pk=ticket.pk).exists())
        self.assertFalse(GeneratedDocument.objects.filter(ticket_id=ticket.pk).exists())

    @patch("qq.services.push_notifications.Thread")
    def test_notification_push_is_started_in_background_after_commit(self, thread):
        appointment = Appointment.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            service=self.service,
            appointment_date=date.today(),
            time_slot=self.time_slot,
            queue_number="DOC-003",
        )
        with self.captureOnCommitCallbacks(execute=True):
            notification = Notification.objects.create(
                resident=self.resident,
                appointment=appointment,
                notification_type=Notification.NotificationType.QUEUE_UPDATE,
                title="Queue update",
                message="Your queue changed.",
            )

        thread.assert_called_once()
        self.assertEqual(thread.call_args.kwargs["args"], (notification.pk,))
        self.assertTrue(thread.call_args.kwargs["daemon"])
        thread.return_value.start.assert_called_once_with()

    def test_transaction_action_cannot_access_another_residents_appointment(self):
        other_user = User.objects.create_user(username="other-resident", password="secret")
        other = Resident.objects.create(
            user=other_user,
            first_name="Other",
            last_name="Resident",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.FEMALE,
            contact_number="09333333333",
            barangay=self.barangay,
        )
        appointment = Appointment.objects.create(
            resident=other,
            barangay=self.barangay,
            service=self.service,
            appointment_date=date.today(),
            time_slot=self.time_slot,
            queue_number="DOC-002",
        )

        response = self.client.post(
            "/api/transactions/",
            {"appointment_id": appointment.pk, "action": "cancel"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
