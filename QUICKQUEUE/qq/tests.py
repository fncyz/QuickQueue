from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from qq.models import (
    Appointment,
    Barangay,
    BarangayStaff,
    DocumentTemplate,
    GeneratedDocument,
    Notification,
    EventBooking,
    QueueTicket,
    Resident,
    Service,
    TimeSlot,
)
from qq.services.appointment_service import check_duplicate_appointment, check_timeslot_capacity


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

    def test_completed_resident_can_sign_in_with_pin(self):
        user = User.objects.create_user(username="pinresident", password="StrongPass1!")
        Resident.objects.create(
            user=user,
            first_name="PIN",
            last_name="Resident",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.MALE,
            contact_number="09888888888",
            barangay=self.barangay,
            pin_hash=make_password("4826"),
            security_setup_stage=Resident.SecuritySetupStage.COMPLETE,
        )

        response = self.client.post("/api/login/pin/", {
            "username": "pinresident",
            "pin": "4826",
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["security_setup_stage"], "complete")


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
        booking_date = timezone.localdate() + timedelta(days=1)
        while booking_date.weekday() >= 5:
            booking_date += timedelta(days=1)
        payload = {
            "service": self.service.pk,
            "time_slot": self.time_slot.pk,
            "appointment_date": booking_date.isoformat(),
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

    def test_completed_and_missed_appointments_keep_occupying_slots(self):
        booking_date = timezone.localdate() + timedelta(days=1)
        completed = Appointment.objects.create(
            resident=self.resident, barangay=self.barangay, service=self.service,
            appointment_date=booking_date, time_slot=self.time_slot,
            queue_number="DOC-101", status=Appointment.Status.COMPLETED,
        )
        self.assertTrue(check_duplicate_appointment(self.resident, booking_date, self.time_slot))

        completed.status = Appointment.Status.MISSED
        completed.save(update_fields=["status", "updated_at"])
        self.assertTrue(check_duplicate_appointment(self.resident, booking_date, self.time_slot))

        self.time_slot.max_appointments = 1
        self.time_slot.save(update_fields=["max_appointments", "updated_at"])
        self.assertFalse(check_timeslot_capacity(booking_date, self.time_slot))

    def test_cancelled_appointment_releases_its_slot(self):
        booking_date = timezone.localdate() + timedelta(days=1)
        Appointment.objects.create(
            resident=self.resident, barangay=self.barangay, service=self.service,
            appointment_date=booking_date, time_slot=self.time_slot,
            queue_number="DOC-102", status=Appointment.Status.CANCELLED,
        )
        self.assertFalse(check_duplicate_appointment(self.resident, booking_date, self.time_slot))
        self.assertTrue(check_timeslot_capacity(booking_date, self.time_slot))

    def test_time_slot_capacity_is_shared_across_regular_services(self):
        booking_date = timezone.localdate() + timedelta(days=1)
        while booking_date.weekday() >= 5:
            booking_date += timedelta(days=1)
        other_service = Service.objects.create(
            code="IND", name="Indigency Test Service", description="Test service",
            estimated_duration=15,
        )
        self.time_slot.max_appointments = 10
        self.time_slot.save(update_fields=["max_appointments", "updated_at"])
        for index in range(5):
            user = User.objects.create_user(username=f"shared-slot-{index}", password="secret")
            resident = Resident.objects.create(
                user=user, first_name="Shared", last_name=f"Resident {index}",
                birthdate=date(2000, 1, 1), sex=Resident.Sex.MALE,
                contact_number=f"0910000000{index}", barangay=self.barangay,
            )
            Appointment.objects.create(
                resident=resident, barangay=self.barangay,
                service=self.service if index % 2 == 0 else other_service,
                appointment_date=booking_date, time_slot=self.time_slot,
                queue_number=f"S{index + 1:02d}", status=Appointment.Status.CONFIRMED,
            )

        availability = self.client.get(
            f"/api/appointments/?appointment_date={booking_date.isoformat()}"
        )
        slot = next(item for item in availability.data["time_slots"] if item["id"] == self.time_slot.pk)
        self.assertEqual(slot["occupied"], 5)
        self.assertEqual(slot["capacity"], 5)
        self.assertEqual(slot["remaining"], 0)
        self.assertTrue(slot["is_fully_booked"])
        self.assertFalse(slot["is_available"])
        self.assertIn("Fully Booked", slot["label"])

        response = self.client.post("/api/appointments/", {
            "service": other_service.pk,
            "time_slot": self.time_slot.pk,
            "appointment_date": booking_date.isoformat(),
            "purpose": "Sixth shared booking",
            "sitio": "Test Sitio",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("already full", response.data["message"])
        self.assertEqual(Appointment.objects.filter(
            appointment_date=booking_date, time_slot=self.time_slot,
        ).exclude(status=Appointment.Status.CANCELLED).count(), 5)

    def test_past_date_booking_is_rejected_by_service(self):
        response = self.client.post("/api/appointments/", {
            "service": self.service.pk,
            "time_slot": self.time_slot.pk,
            "appointment_date": (timezone.localdate() - timedelta(days=1)).isoformat(),
            "purpose": "Past booking attempt",
            "sitio": "Test Sitio",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Appointment.objects.filter(resident=self.resident).exists())

    def test_staff_calendar_closes_past_date_without_resetting_count(self):
        past_date = timezone.localdate() - timedelta(days=1)
        for index, status_value in enumerate((
            Appointment.Status.COMPLETED,
            Appointment.Status.MISSED,
            Appointment.Status.CANCELLED,
        ), start=1):
            Appointment.objects.create(
                resident=self.resident, barangay=self.barangay, service=self.service,
                appointment_date=past_date, time_slot=self.time_slot,
                queue_number=f"DOC-{index:03d}", status=status_value,
            )

        staff_user = User.objects.create_user(username="calendar-staff", password="secret")
        BarangayStaff.objects.create(
            user=staff_user, barangay=self.barangay, first_name="Calendar",
            last_name="Staff", username="calendar-staff", role=BarangayStaff.Role.STAFF,
        )
        self.client.force_authenticate(user=None)
        self.client.force_login(staff_user)

        response = self.client.get(f"/barangay/staff/appointments/?date={past_date.isoformat()}")

        self.assertEqual(response.status_code, 200)
        day = next(
            item for week in response.context["calendar_weeks"] for item in week
            if item["date"] == past_date
        )
        self.assertEqual(day["count"], 2)
        self.assertEqual(day["level"], "closed")
        self.assertContains(response, "Closed")
        self.assertContains(response, "2/5")

    def test_regular_booking_rejects_weekends(self):
        saturday = date.today() + timedelta(days=(5 - date.today().weekday()) % 7)
        if saturday < date.today():
            saturday += timedelta(days=7)
        response = self.client.post("/api/appointments/", {
            "service": self.service.pk,
            "time_slot": self.time_slot.pk,
            "appointment_date": saturday.isoformat(),
            "purpose": "Weekend booking attempt",
            "sitio": "Test Sitio",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Monday through Friday", response.data["message"])
        self.assertFalse(Appointment.objects.filter(resident=self.resident).exists())

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

    def test_temporary_service_statuses_and_server_side_booking_window(self):
        today = timezone.localdate()
        temporary = Service.objects.create(
            code="EVT", name="Medical Mission Test", description="Temporary care",
            estimated_duration=15, is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT, barangay=self.barangay,
            event_start_date=today + timedelta(days=7), event_end_date=today + timedelta(days=7),
            booking_start_date=today + timedelta(days=1), booking_end_date=today + timedelta(days=6),
            capacity=1,
        )

        summary = self.client.get("/api/appointments/?summary=1")
        event = next(item for item in summary.data["temporary_services"] if item["id"] == temporary.pk)
        self.assertEqual(event["status"], "upcoming")
        self.assertFalse(event["can_book"])
        self.assertNotIn(temporary.pk, [item["id"] for item in summary.data["services"]])

        payload = {"service": temporary.pk}
        early = self.client.post("/api/appointments/", payload, format="json")
        self.assertEqual(early.status_code, 400)
        self.assertIn("not yet", early.data["message"])

        temporary.booking_start_date = today - timedelta(days=1)
        temporary.booking_end_date = today + timedelta(days=1)
        temporary.save(update_fields=["booking_start_date", "booking_end_date"])
        booked = self.client.post("/api/appointments/", payload, format="json")
        self.assertEqual(booked.status_code, 201)
        self.assertTrue(booked.data["is_event"])
        self.assertTrue(booked.data["booking_reference"].startswith("EVT-"))
        event_booking = EventBooking.objects.get(appointment_id=booked.data["id"])
        self.assertFalse(QueueTicket.objects.filter(appointment_id=booked.data["id"]).exists())
        self.assertIsNone(event_booking.appointment.time_slot)

        duplicate = self.client.post("/api/appointments/", payload, format="json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(EventBooking.objects.filter(appointment__resident=self.resident, appointment__service=temporary).count(), 1)

        event_pass = self.client.get(f"/api/event-bookings/{event_booking.pk}/pass/")
        self.assertEqual(event_pass.status_code, 200)
        self.assertEqual(event_pass.data["booking_reference"], event_booking.booking_reference)
        self.assertEqual(EventBooking.booking_id_from_token(event_pass.data["qr_token"]), event_booking.booking_id)

        summary = self.client.get("/api/appointments/?summary=1")
        event = next(item for item in summary.data["temporary_services"] if item["id"] == temporary.pk)
        self.assertEqual(event["status"], "fully_booked")
        self.assertFalse(event["can_book"])

    def test_expired_and_cancelled_temporary_services_are_hidden(self):
        today = timezone.localdate()
        for suffix, lifecycle, end in (
            ("Expired", Service.Lifecycle.SCHEDULED, today - timedelta(days=1)),
            ("Cancelled", Service.Lifecycle.CANCELLED, today + timedelta(days=1)),
        ):
            Service.objects.create(
                code="EVT", name=f"Hidden Event {suffix}", description="Hidden",
                estimated_duration=15, is_temporary=True,
                temporary_type=Service.TemporaryType.EVENT, barangay=self.barangay,
                event_start_date=today + timedelta(days=2), event_end_date=today + timedelta(days=2),
                booking_start_date=today - timedelta(days=2), booking_end_date=end,
                capacity=10, lifecycle=lifecycle,
            )
        summary = self.client.get("/api/appointments/?summary=1")
        names = {item["name"] for item in summary.data["temporary_services"]}
        self.assertNotIn("Hidden Event Expired", names)
        self.assertNotIn("Hidden Event Cancelled", names)

    def test_staff_event_qr_checkin_is_atomic_and_cannot_be_reused(self):
        today = timezone.localdate()
        event = Service.objects.create(
            code="SCAN", name="Scanner Event Test", description="Scan test", estimated_duration=15,
            is_temporary=True, temporary_type=Service.TemporaryType.EVENT, barangay=self.barangay,
            event_start_date=today - timedelta(days=1), event_end_date=today + timedelta(days=1),
            booking_start_date=today - timedelta(days=7), booking_end_date=today,
            capacity=10,
        )
        appointment = Appointment.objects.create(
            resident=self.resident, barangay=self.barangay, service=event,
            appointment_date=date.today(), time_slot=None, queue_number="",
        )
        booking = EventBooking.objects.create(appointment=appointment)
        staff_user = User.objects.create_user(username="event-scanner", password="secret")
        BarangayStaff.objects.create(
            user=staff_user, barangay=self.barangay, first_name="Event", last_name="Staff",
            username="event-scanner", role=BarangayStaff.Role.STAFF,
        )
        self.client.force_authenticate(user=None)
        self.client.force_login(staff_user)
        token = booking.qr_token()

        valid = self.client.post("/barangay/staff/events/scanner/", {"token": token}, format="json")
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["result"], "valid")

        checked = self.client.post("/barangay/staff/events/scanner/", {"token": token, "action": "check_in"}, format="json")
        self.assertEqual(checked.status_code, 200)
        booking.refresh_from_db()
        first_checked_at = booking.checked_in_at
        self.assertEqual(booking.status, EventBooking.Status.CHECKED_IN)

        reused = self.client.post("/barangay/staff/events/scanner/", {"token": token, "action": "check_in"}, format="json")
        self.assertEqual(reused.status_code, 409)
        self.assertEqual(reused.json()["message"], "Already Checked In")
        booking.refresh_from_db()
        self.assertEqual(booking.checked_in_at, first_checked_at)

        invalid = self.client.post("/barangay/staff/events/scanner/", {"token": token + "tampered"}, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["message"], "Invalid QR Code")
