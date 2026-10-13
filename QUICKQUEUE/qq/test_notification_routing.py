from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from qq.models import Appointment, Barangay, BarangayStaff, Notification, Resident, Service
from qq.services.notification_service import notify_barangay_staff, notify_resident


class RoleBasedNotificationTests(TestCase):
    def setUp(self):
        self.barangay = Barangay.objects.get(name="Poblacion")
        self.other_barangay = Barangay.objects.get(name="Bato")
        self.service = Service.objects.filter(is_temporary=False).first()
        self.resident_user = User.objects.create_user("routing-resident", password="password")
        self.resident = Resident.objects.create(
            user=self.resident_user, first_name="Routing", last_name="Resident",
            birthdate="1990-01-01", sex=Resident.Sex.FEMALE,
            email="routing@example.com", contact_number="09171111111", barangay=self.barangay,
        )
        self.appointment = Appointment.objects.create(
            resident=self.resident, barangay=self.barangay, service=self.service,
            appointment_date=date.today(), queue_number="A-005",
        )
        self.staff_user = User.objects.create_user("routing-staff", password="password")
        BarangayStaff.objects.create(
            user=self.staff_user, barangay=self.barangay, first_name="Right", last_name="Staff",
            username=self.staff_user.username, role=BarangayStaff.Role.STAFF,
        )
        self.other_staff_user = User.objects.create_user("other-routing-staff", password="password")
        BarangayStaff.objects.create(
            user=self.other_staff_user, barangay=self.other_barangay, first_name="Other", last_name="Staff",
            username=self.other_staff_user.username, role=BarangayStaff.Role.STAFF,
        )

    def test_staff_alert_is_isolated_by_barangay_and_deduplicated(self):
        for _ in range(2):
            notify_barangay_staff(
                appointment=self.appointment, title="Resident Checked In",
                message="Routing Resident checked in. Queue A-005.",
                event_key=f"appointment:{self.appointment.pk}:check-in",
            )

        alerts = Notification.objects.filter(recipient_role=Notification.RecipientRole.STAFF)
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.get().recipient, self.staff_user)
        self.assertFalse(alerts.filter(recipient=self.other_staff_user).exists())

    def test_resident_api_cannot_read_another_users_notification(self):
        own = notify_resident(
            appointment=self.appointment,
            notification_type=Notification.NotificationType.APPOINTMENT_CONFIRMED,
            title="Appointment Confirmed", message="Your appointment is confirmed.",
            event_key=f"appointment:{self.appointment.pk}:confirmed",
        )
        other_user = User.objects.create_user("other-routing-resident", password="password")
        other_resident = Resident.objects.create(
            user=other_user, first_name="Other", last_name="Resident", birthdate="1990-01-01",
            sex=Resident.Sex.MALE, email="other-routing@example.com",
            contact_number="09172222222", barangay=self.other_barangay,
        )
        other_appointment = Appointment.objects.create(
            resident=other_resident, barangay=self.other_barangay, service=self.service,
            appointment_date=date.today(), queue_number="B-001",
        )
        hidden = notify_resident(
            appointment=other_appointment,
            notification_type=Notification.NotificationType.QUEUE_UPDATE,
            title="Now Serving", message="Your number is called.",
            event_key=f"appointment:{other_appointment.pk}:called",
        )
        client = APIClient()
        client.force_authenticate(self.resident_user)

        response = client.get("/api/notifications/")

        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data["notifications"]}
        self.assertIn(own.pk, ids)
        self.assertNotIn(hidden.pk, ids)

    def test_staff_alert_does_not_enter_resident_history(self):
        notify_barangay_staff(
            appointment=self.appointment, title="New Appointment", message="Staff action required.",
            event_key=f"appointment:{self.appointment.pk}:staff-created",
        )
        client = APIClient()
        client.force_authenticate(self.resident_user)

        response = client.get("/api/notifications/")

        self.assertEqual(response.data["notifications"], [])
