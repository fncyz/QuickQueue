from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from qq.models import Appointment, Barangay, BarangayStaff, QueueTicket, Resident, Service, TimeSlot


class AdminStaffWorkflowTests(TestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Workflow Test Barangay",
            address="Toledo City",
            contact_number="09123456789",
        )
        self.admin_user = User.objects.create_user(username="workflow-admin", password="secret")
        self.barangay.user = self.admin_user
        self.barangay.save(update_fields=["user", "updated_at"])
        self.staff_user = User.objects.create_user(username="workflow-staff", password="secret")
        BarangayStaff.objects.create(
            barangay=self.barangay,
            user=self.staff_user,
            first_name="Workflow",
            last_name="Staff",
            username="workflow-staff",
            role=BarangayStaff.Role.STAFF,
        )
        self.slot = TimeSlot.objects.create(
            barangay=self.barangay,
            start_time=time(8),
            end_time=time(9),
            max_appointments=5,
        )
        self.service = Service.objects.create(
            code="CLR",
            name="Clearance Workflow Test",
            description="Test",
            estimated_duration=15,
        )
        self.other_service = Service.objects.create(
            code="IND",
            name="Indigency Workflow Test",
            description="Test",
            estimated_duration=15,
        )
        self.client.force_login(self.staff_user)

    def _ticket(self, username, first_name, service, queue_number):
        user = User.objects.create_user(username=username, password="secret")
        resident = Resident.objects.create(
            user=user,
            first_name=first_name,
            last_name="Resident",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.MALE,
            contact_number=f"0917{user.pk:07d}",
            barangay=self.barangay,
        )
        appointment = Appointment.objects.create(
            resident=resident,
            barangay=self.barangay,
            service=service,
            appointment_date=timezone.localdate(),
            time_slot=self.slot,
            queue_number=queue_number,
            status=Appointment.Status.CONFIRMED,
        )
        return QueueTicket.objects.create(appointment=appointment, queue_number=queue_number)

    def test_staff_dashboard_uses_direct_staff_workflow_links(self):
        response = self.client.get("/barangay/staff/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Barangay Workflow Test Barangay Staff Portal")
        self.assertContains(response, 'href="/barangay/staff/appointments/"')
        self.assertContains(response, 'href="/barangay/staff/queue/live/"')
        self.assertContains(response, 'href="/barangay/staff/documents/"')

    def test_admin_dashboard_opens_live_queue_directly(self):
        self.client.force_login(self.admin_user)

        response = self.client.get("/barangay/dashboard/")

        self.assertEqual(response.status_code, 200)
        # Sidebar plus both dashboard shortcuts lead to the actual queue page.
        self.assertContains(response, 'href="/barangay/queue/live/"', count=3)

    def test_staff_queue_filters_by_resident_and_service(self):
        matching = self._ticket("ana", "Ana", self.service, "C01")
        self._ticket("ben", "Ben", self.other_service, "I01")

        response = self.client.get(
            f"/barangay/staff/queue/live/?slot={self.slot.pk}&q=Ana&service={self.service.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([ticket.pk for ticket in response.context["tickets"]], [matching.pk])
        self.assertEqual(response.context["filters"], {"q": "Ana", "service": str(self.service.pk)})

    def test_staff_queue_action_returns_to_staff_portal(self):
        response = self.client.post("/barangay/queue/call-next/", {"slot": self.slot.pk})

        self.assertRedirects(
            response,
            f"/barangay/staff/queue/live/?slot={self.slot.pk}",
            fetch_redirect_response=False,
        )

    def test_staff_documents_are_consolidated_with_processing_and_completed_tabs(self):
        response = self.client.get("/barangay/staff/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ">Documents</a>")
        self.assertContains(response, "For Processing")
        self.assertContains(response, "Completed")
        self.assertNotContains(response, ">Document Processing</a>")
        self.assertNotContains(response, ">Completed Documents</a>")
        self.assertNotContains(response, ">Resident Logbook</a>")

        completed = self.client.get("/barangay/staff/documents/?tab=completed")
        self.assertEqual(completed.status_code, 200)
        self.assertContains(completed, "Completed document archive")

    def test_legacy_document_and_logbook_routes_redirect_to_unified_pages(self):
        completed = self.client.get("/barangay/staff/documents/completed/")
        self.assertRedirects(
            completed,
            "/barangay/staff/documents/?tab=completed",
            fetch_redirect_response=False,
        )
        history = self.client.get("/barangay/staff/residents/")
        self.assertRedirects(
            history,
            "/barangay/staff/appointments/?tab=history",
            fetch_redirect_response=False,
        )

    def test_resident_history_is_available_inside_appointments(self):
        response = self.client.get("/barangay/staff/appointments/?tab=history")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resident History")
        self.assertContains(response, "Completed resident service history")

    def test_document_processing_action_still_updates_existing_ticket(self):
        ticket = self._ticket("document-resident", "Document", self.service, "C09")

        response = self.client.post(
            f"/barangay/staff/documents/{ticket.pk}/action/",
            {"action": "start"},
        )

        self.assertRedirects(response, "/barangay/staff/documents/", fetch_redirect_response=False)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)
