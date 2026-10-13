from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase

from qq.models import Appointment, Barangay, BarangayStaff, QueueTicket, Resident, Service, ServiceWindow, TimeSlot


class WindowManagementTests(TestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Window Test", address="Toledo", contact_number="09120000000")
        self.admin_user = User.objects.create_user("window-admin", password="secret")
        self.barangay.user = self.admin_user
        self.barangay.save(update_fields=("user", "updated_at"))
        BarangayStaff.objects.create(barangay=self.barangay, user=self.admin_user, first_name="Admin", last_name="User", username="window-admin", role=BarangayStaff.Role.ADMIN)
        self.staff_user = User.objects.create_user("window-staff", password="secret")
        self.staff = BarangayStaff.objects.create(barangay=self.barangay, user=self.staff_user, first_name="Queue", last_name="Staff", username="window-staff", role=BarangayStaff.Role.STAFF)
        self.client.force_login(self.admin_user)

    def test_admin_configures_and_assigns_windows_without_duplicates(self):
        response = self.client.post("/barangay/settings/?tab=windows", {"action": "window_count", "total_windows": 3})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ServiceWindow.objects.filter(barangay=self.barangay).count(), 3)
        self.client.post("/barangay/settings/?tab=windows", {"action": "window_count", "total_windows": 3})
        self.assertEqual(ServiceWindow.objects.filter(barangay=self.barangay).count(), 3)
        window = ServiceWindow.objects.get(barangay=self.barangay, number=1)
        self.client.post("/barangay/settings/?tab=windows", {"action": "window_update", "window_id": window.pk, "name": "Front Desk", "assigned_staff": self.staff.pk, "is_active": "on"})
        window.refresh_from_db()
        self.assertEqual(window.assigned_staff, self.staff)
        self.assertEqual(window.name, "Front Desk")

    def test_staff_claim_records_assigned_window_and_staff(self):
        window = ServiceWindow.objects.create(barangay=self.barangay, number=1, name="Window 1", assigned_staff=self.staff)
        slot = TimeSlot.objects.create(barangay=self.barangay, start_time=time(8), end_time=time(9), max_appointments=5)
        service = Service.objects.create(code="WQ", name="Window Queue Test", description="Test", estimated_duration=10)
        resident_user = User.objects.create_user("window-resident", password="secret")
        resident = Resident.objects.create(user=resident_user, first_name="Window", last_name="Resident", birthdate=date(2000, 1, 1), sex=Resident.Sex.MALE, contact_number="09121111111", barangay=self.barangay)
        appointment = Appointment.objects.create(resident=resident, barangay=self.barangay, service=service, appointment_date=date.today(), time_slot=slot, queue_number="W-001", status=Appointment.Status.CONFIRMED)
        ticket = QueueTicket.objects.create(appointment=appointment, queue_number="W-001")
        self.client.force_login(self.staff_user)
        response = self.client.post("/barangay/queue/call-next/", {"slot": slot.pk})
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.NOW_SERVING)
        self.assertEqual(ticket.service_window, window)
        self.assertEqual(ticket.served_by, self.staff)

    def test_live_monitor_counts_active_windows_for_current_barangay(self):
        ServiceWindow.objects.create(barangay=self.barangay, number=1, name="Window 1", is_active=True)
        ServiceWindow.objects.create(barangay=self.barangay, number=2, name="Window 2", is_active=True)
        ServiceWindow.objects.create(barangay=self.barangay, number=3, name="Window 3", is_active=False)

        other_barangay = Barangay.objects.create(name="Other Barangay", address="Toledo", contact_number="09123333333")
        ServiceWindow.objects.create(barangay=other_barangay, number=1, name="Other Window", is_active=True)

        response = self.client.get("/barangay/queue/live/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["active_windows"], 2)
        self.assertContains(response, "Active Windows")
