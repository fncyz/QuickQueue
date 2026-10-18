from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

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
from qq.services.timeslot_service import ensure_default_time_slots, regular_slot_capacities


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

    def test_booking_management_persists_capacity_for_staff_barangay_only(self):
        other_barangay = Barangay.objects.create(
            name="Other Capacity Barangay",
            address="Toledo City",
            contact_number="09123450000",
        )
        self.client.force_login(self.staff_user)

        page = self.client.get(f"{reverse('staff_settings')}?tab=booking")
        self.assertContains(page, "Booking Management")
        self.assertContains(
            page,
            "Manage the number of appointment slots available for residents each day.",
        )
        self.assertContains(page, 'value="30"')

        response = self.client.post(reverse("staff_settings"), {
            "action": "booking",
            "daily_booking_capacity": "32",
        })

        self.assertRedirects(
            response,
            f"{reverse('staff_settings')}?tab=booking",
            fetch_redirect_response=False,
        )
        self.barangay.refresh_from_db()
        other_barangay.refresh_from_db()
        self.assertEqual(self.barangay.daily_booking_capacity, 32)
        self.assertEqual(other_barangay.daily_booking_capacity, 30)

    def test_booking_management_rejects_non_positive_and_fractional_values(self):
        self.client.force_login(self.staff_user)
        for value in ("0", "-1", "2.5", ""):
            with self.subTest(value=value):
                response = self.client.post(
                    reverse("staff_settings"),
                    {"action": "booking", "daily_booking_capacity": value},
                    follow=True,
                )
                self.assertContains(response, "must be a positive whole number")
                self.barangay.refresh_from_db()
                self.assertEqual(self.barangay.daily_booking_capacity, 30)

    def test_capacity_is_distributed_in_time_order_across_existing_slots(self):
        ensure_default_time_slots(self.barangay)
        self.barangay.daily_booking_capacity = 32
        self.barangay.save(update_fields=["daily_booking_capacity", "updated_at"])
        slots = list(TimeSlot.objects.filter(
            barangay=self.barangay,
            is_active=True,
        ).order_by("start_time"))

        capacities = regular_slot_capacities(self.barangay, slots)

        self.assertEqual([capacities[slot.pk] for slot in slots], [6, 6, 5, 5, 5, 5])

    def test_configured_capacity_reaches_resident_api_and_staff_calendar(self):
        ensure_default_time_slots(self.barangay)
        self.barangay.daily_booking_capacity = 32
        self.barangay.save(update_fields=["daily_booking_capacity", "updated_at"])

        resident_client = APIClient()
        resident_client.force_authenticate(self.resident.user)
        api_response = resident_client.get(
            f"/api/appointments/?appointment_date={self.appointment_date.isoformat()}"
        )
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            [slot["capacity"] for slot in api_response.json()["time_slots"]],
            [6, 6, 5, 5, 5, 5],
        )

        self.client.force_login(self.staff_user)
        calendar_response = self.client.get(
            f"{reverse('staff_appointments')}?date={self.appointment_date.isoformat()}"
        )
        self.assertEqual(calendar_response.context["daily_capacity"], 32)
        self.assertEqual(
            [slot["capacity"] for slot in calendar_response.context["selected_slots"]],
            [6, 6, 5, 5, 5, 5],
        )

    def test_reducing_capacity_warns_and_preserves_existing_bookings(self):
        second_user = User.objects.create_user(username="capacity-resident-two", password="secret")
        second_resident = Resident.objects.create(
            user=second_user,
            first_name="Second",
            last_name="Resident",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.FEMALE,
            contact_number="09170000002",
            barangay=self.barangay,
        )
        for index, resident in enumerate((self.resident, second_resident), start=1):
            Appointment.objects.create(
                resident=resident,
                barangay=self.barangay,
                service=self.service,
                appointment_date=self.appointment_date,
                time_slot=self.slot,
                queue_number=f"CFG-{index:02d}",
                status=Appointment.Status.CONFIRMED,
            )
        self.client.force_login(self.staff_user)

        response = self.client.post(reverse("staff_settings"), {
            "action": "booking",
            "daily_booking_capacity": "1",
        }, follow=True)

        self.assertContains(response, "2 existing appointments")
        self.assertEqual(Appointment.objects.count(), 2)
        self.barangay.refresh_from_db()
        self.assertEqual(self.barangay.daily_booking_capacity, 1)
