from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from qq.models import (
    Appointment,
    Barangay,
    BarangayServiceConfiguration,
    BarangayStaff,
    ClosedAppointmentDate,
    Resident,
    Service,
    TimeSlot,
)
from qq.services.appointment_service import create_appointment


class BookingConfigurationTests(TestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Configuration Test Barangay",
            address="Toledo City",
            contact_number="09123456789",
        )
        self.admin_user = User.objects.create_user(username="configuration-admin", password="secret")
        self.barangay.user = self.admin_user
        self.barangay.save(update_fields=["user", "updated_at"])
        self.staff_user = User.objects.create_user(username="configuration-staff", password="secret")
        BarangayStaff.objects.create(
            barangay=self.barangay,
            user=self.staff_user,
            first_name="Configuration",
            last_name="Admin",
            username="configuration-staff",
            role=BarangayStaff.Role.STAFF,
        )
        resident_user = User.objects.create_user(username="configuration-resident", password="secret")
        self.resident = Resident.objects.create(
            user=resident_user,
            first_name="Test",
            last_name="Resident",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.MALE,
            contact_number="09170000001",
            barangay=self.barangay,
        )
        self.service = Service.objects.create(
            code="CFG",
            name="Configuration Test Service",
            description="Test",
            estimated_duration=15,
        )
        self.slot = TimeSlot.objects.create(
            barangay=self.barangay,
            start_time=time(8),
            end_time=time(9),
            max_appointments=5,
        )
        candidate = timezone.localdate() + timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        self.appointment_date = candidate

    def test_staff_can_save_barangay_specific_service_configuration(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("staff_settings"),
            {
                "action": "service",
                "service_id": self.service.pk,
                "fee": "75.50",
                "estimated_duration": "25",
            },
        )

        self.assertRedirects(response, f"{reverse('staff_settings')}?tab=services", fetch_redirect_response=False)
        configuration = BarangayServiceConfiguration.objects.get(
            barangay=self.barangay, service=self.service
        )
        self.assertEqual(configuration.fee, Decimal("75.50"))
        self.assertEqual(configuration.estimated_duration, 25)
        self.assertEqual(self.service.estimated_duration, 15)
        page = self.client.get(f"{reverse('staff_settings')}?tab=services")
        self.assertContains(page, "Service Management")
        self.assertContains(page, "75.50")

    def test_valid_regular_booking_is_auto_confirmed_with_fee_snapshot(self):
        BarangayServiceConfiguration.objects.create(
            barangay=self.barangay,
            service=self.service,
            fee=Decimal("50.00"),
            estimated_duration=20,
        )

        appointment = create_appointment(
            self.resident,
            self.service,
            self.appointment_date,
            self.slot,
            "Document request",
        )

        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(appointment.service_fee_snapshot, Decimal("50.00"))

    def test_closed_date_blocks_booking_without_deleting_history(self):
        ClosedAppointmentDate.objects.create(
            barangay=self.barangay,
            date=self.appointment_date,
            reason="Barangay holiday",
            created_by=self.staff_user,
        )

        with self.assertRaisesMessage(ValueError, "Appointments are unavailable on this date"):
            create_appointment(
                self.resident,
                self.service,
                self.appointment_date,
                self.slot,
                "Document request",
            )

        self.assertFalse(Appointment.objects.exists())
