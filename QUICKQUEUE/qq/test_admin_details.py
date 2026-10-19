from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone

from qq.models import (
    Appointment,
    Barangay,
    BarangayStaff,
    EventBooking,
    QueueTicket,
    Resident,
    Service,
    ServiceWindow,
    TimeSlot,
)


class BarangayAdminDetailsTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user("details-admin", password="secret")
        self.barangay = Barangay.objects.create(
            name="Details Barangay",
            address="Toledo City",
            contact_number="09120000101",
            user=self.admin_user,
        )
        self.staff_user = User.objects.create_user("details-staff", password="secret")
        self.staff = BarangayStaff.objects.create(
            barangay=self.barangay,
            user=self.staff_user,
            first_name="Detail",
            last_name="Staff",
            username="details-staff",
            role=BarangayStaff.Role.STAFF,
        )
        self.window = ServiceWindow.objects.create(
            barangay=self.barangay,
            number=1,
            name="Records Window",
            assigned_staff=self.staff,
        )
        resident_user = User.objects.create_user("details-resident", password="secret")
        self.resident = Resident.objects.create(
            user=resident_user,
            first_name="Modal",
            last_name="Resident",
            birthdate=date(1990, 1, 2),
            sex=Resident.Sex.FEMALE,
            email="modal@example.com",
            contact_number="09120000102",
            barangay=self.barangay,
        )
        self.slot = TimeSlot.objects.create(
            barangay=self.barangay,
            start_time=time(8),
            end_time=time(9),
            max_appointments=10,
        )
        self.service = Service.objects.create(
            code="MODAL",
            name="Modal Service",
            description="Details modal service",
            estimated_duration=10,
        )
        self.appointment = Appointment.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            service=self.service,
            appointment_date=timezone.localdate(),
            time_slot=self.slot,
            queue_number="M-001",
            purpose="Modal verification",
            sitio="Purok 1",
            status=Appointment.Status.COMPLETED,
        )
        self.ticket = QueueTicket.objects.create(
            appointment=self.appointment,
            queue_number="M-001",
            status=QueueTicket.Status.COMPLETED,
            service_window=self.window,
            served_by=self.staff,
            called_at=timezone.now(),
            completed_at=timezone.now(),
        )
        self.client.force_login(self.admin_user)

    def detail_url(self, kind, pk):
        return reverse("barangay_admin_record_detail", args=[kind, pk])

    def test_admin_detail_endpoint_returns_authorized_record_information(self):
        appointment = self.client.get(self.detail_url("appointment", self.appointment.pk))
        resident = self.client.get(self.detail_url("resident", self.resident.pk))
        queue = self.client.get(self.detail_url("queue-ticket", self.ticket.pk))

        self.assertEqual(appointment.status_code, 200)
        self.assertEqual(appointment.json()["title"], "Appointment Details")
        self.assertIn("Modal Resident", str(appointment.json()["sections"]))
        self.assertIn("Modal Service", str(appointment.json()["sections"]))
        self.assertEqual(resident.status_code, 200)
        self.assertIn("modal@example.com", str(resident.json()["sections"]))
        self.assertIn("Active", str(resident.json()["sections"]))
        self.assertEqual(queue.status_code, 200)
        self.assertIn("Records Window", str(queue.json()["sections"]))
        self.assertIn("Detail Staff", str(queue.json()["sections"]))

    def test_special_service_details_use_booking_reference_and_omit_regular_fields(self):
        special_service = Service.objects.create(
            code="EVENT",
            name="Community Event",
            description="Special service details",
            estimated_duration=10,
            is_temporary=True,
            barangay=self.barangay,
        )
        appointment = Appointment.objects.create(
            resident=self.resident,
            barangay=self.barangay,
            service=special_service,
            appointment_date=timezone.localdate(),
            queue_number="",
            purpose="Must not be shown",
            sitio="Must not be shown",
            status=Appointment.Status.CONFIRMED,
        )
        booking = EventBooking.objects.create(appointment=appointment)

        response = self.client.get(self.detail_url("appointment", appointment.pk))

        self.assertEqual(response.status_code, 200)
        fields = [
            field
            for section in response.json()["sections"]
            for field in section["fields"]
        ]
        labels = {field["label"] for field in fields}
        values = {field["value"] for field in fields}
        self.assertIn("Booking Reference", labels)
        self.assertIn(booking.booking_reference, values)
        self.assertNotIn("Queue Number", labels)
        self.assertNotIn("Time Slot", labels)
        self.assertNotIn("Purpose", labels)
        self.assertNotIn("Sitio / Purok", labels)

    def test_regular_service_details_keep_queue_purpose_and_sitio(self):
        response = self.client.get(self.detail_url("appointment", self.appointment.pk))

        fields = [
            field
            for section in response.json()["sections"]
            for field in section["fields"]
        ]
        labels = {field["label"] for field in fields}
        self.assertIn("Queue Number", labels)
        self.assertIn("Time Slot", labels)
        self.assertIn("Purpose", labels)
        self.assertIn("Sitio / Purok", labels)
        self.assertNotIn("Booking Reference", labels)

    def test_resident_rows_only_show_the_view_action(self):
        response = self.client.get(reverse("barangay_residents"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="#resident-{self.resident.pk}"')
        self.assertNotContains(response, 'class="btn-more"')
        self.assertContains(response, "qq/js/admin_details_modal.js")

    def test_detail_endpoint_rejects_cross_barangay_records_and_regular_staff(self):
        foreign_user = User.objects.create_user("foreign-detail", password="secret")
        foreign_barangay = Barangay.objects.create(
            name="Foreign Details",
            address="Toledo City",
            contact_number="09120000103",
        )
        foreign_resident = Resident.objects.create(
            user=foreign_user,
            first_name="Foreign",
            last_name="Resident",
            birthdate=date(1991, 1, 1),
            sex=Resident.Sex.MALE,
            contact_number="09120000104",
            barangay=foreign_barangay,
        )

        cross_barangay = self.client.get(self.detail_url("resident", foreign_resident.pk))
        missing = self.client.get(self.detail_url("resident", 999999))
        self.client.force_login(self.staff_user)
        staff_attempt = self.client.get(self.detail_url("resident", self.resident.pk))

        self.assertEqual(cross_barangay.status_code, 404)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(staff_attempt.status_code, 403)

    def test_broken_admin_view_links_are_wired_to_shared_details_modal(self):
        pages = (
            reverse("barangay_appointments"),
            reverse("barangay_residents"),
            reverse("barangay_queue_history"),
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "qq/css/admin_details_modal.css")
                self.assertContains(response, "qq/js/admin_details_modal.js")

        appointments = self.client.get(reverse("barangay_appointments"))
        residents = self.client.get(reverse("barangay_residents"))
        history = self.client.get(reverse("barangay_queue_history"))
        self.assertContains(appointments, f'href="#appointment-{self.appointment.pk}"')
        self.assertContains(residents, f'href="#resident-{self.resident.pk}"')
        self.assertContains(history, f'href="#ticket-{self.ticket.pk}"')

    def test_existing_staff_details_modal_includes_assigned_window(self):
        response = self.client.get(reverse("barangay_staff"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-open-modal="view-staff-')
        self.assertContains(response, "Assigned Window")
        self.assertContains(response, "Records Window")

    def test_admin_view_all_labels_do_not_include_decorative_arrows(self):
        appointments_source = get_template(
            "barangay_admin/appointments.html"
        ).template.source
        history_source = get_template(
            "barangay_admin/queue_history.html"
        ).template.source

        self.assertIn(">View All Regular Services</a>", appointments_source)
        self.assertIn(">View All Special Services</a>", appointments_source)
        self.assertIn(">View All To Be Claimed</a>", history_source)
        self.assertNotIn("View All Regular Services →", appointments_source)
        self.assertNotIn("View All Special Services →", appointments_source)
        self.assertNotIn("View All To Be Claimed →", history_source)
