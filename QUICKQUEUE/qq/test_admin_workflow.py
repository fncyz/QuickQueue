from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from qq.models import (
    Appointment, Barangay, BarangayStaff, EventBooking, Notification, QueueTicket, Resident,
    PushDevice, Service, TimeSlot,
)


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
        self.assertContains(response, "Events &amp; Temporary Services")
        self.assertContains(response, "No upcoming or active events or temporary services.")
        self.assertNotContains(response, "Needs Attention")
        self.assertNotContains(response, "Pickup Notifications")

    def test_staff_dashboard_lists_only_its_upcoming_and_active_offerings(self):
        today = timezone.localdate()
        other_barangay = Barangay.objects.create(
            name="Other Workflow Barangay",
            address="Toledo City",
            contact_number="09999999999",
        )
        visible = Service.objects.create(
            code="EVT",
            name="Staff Dashboard Community Event",
            description="Visible event",
            estimated_duration=15,
            is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT,
            barangay=self.barangay,
            event_start_date=today + timedelta(days=2),
            event_end_date=today + timedelta(days=3),
            booking_start_date=today + timedelta(days=1),
            booking_end_date=today + timedelta(days=2),
            capacity=25,
        )
        Service.objects.create(
            code="OTH",
            name="Other Barangay Private Event",
            description="Must not be visible",
            estimated_duration=15,
            is_temporary=True,
            temporary_type=Service.TemporaryType.SERVICE,
            barangay=other_barangay,
            event_start_date=today + timedelta(days=2),
            event_end_date=today + timedelta(days=3),
            booking_start_date=today,
            booking_end_date=today + timedelta(days=2),
            capacity=25,
        )
        Service.objects.create(
            code="OLD",
            name="Expired Staff Event",
            description="Must not be visible",
            estimated_duration=15,
            is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT,
            barangay=self.barangay,
            event_start_date=today - timedelta(days=3),
            event_end_date=today - timedelta(days=2),
            booking_start_date=today - timedelta(days=5),
            booking_end_date=today - timedelta(days=3),
            capacity=25,
        )

        response = self.client.get("/barangay/staff/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, visible.name)
        self.assertContains(response, f'/barangay/staff/events/{visible.pk}/edit/')
        self.assertContains(response, "Upcoming")
        self.assertNotContains(response, "Other Barangay Private Event")
        self.assertNotContains(response, "Expired Staff Event")

    def test_completed_event_history_preserves_attendance_and_barangay_isolation(self):
        today = timezone.localdate()
        completed = Service.objects.create(
            code="HIST", name="Completed Participant History", description="History test",
            requirements="Valid ID", estimated_duration=15, is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT, barangay=self.barangay,
            location="Covered Court", event_start_date=today - timedelta(days=2),
            event_end_date=today - timedelta(days=1), booking_start_date=today - timedelta(days=8),
            booking_end_date=today - timedelta(days=3), capacity=20,
        )
        active = Service.objects.create(
            code="LIVE", name="Active Scanner Event", description="Active test",
            estimated_duration=15, is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT, barangay=self.barangay,
            event_start_date=today, event_end_date=today + timedelta(days=1),
            booking_start_date=today - timedelta(days=3), booking_end_date=today,
            capacity=20,
        )
        first = self._ticket("history-scanned", "Scanned", self.service, "E01")
        second = self._ticket("history-pending", "Pending", self.service, "E02")
        for ticket in (first, second):
            ticket.appointment.service = completed
            ticket.appointment.save(update_fields=["service", "updated_at"])
        scanned_at = timezone.now() - timedelta(days=1)
        scanned = EventBooking.objects.create(
            appointment=first.appointment, status=EventBooking.Status.CHECKED_IN,
            checked_in_at=scanned_at, checked_in_by=self.staff_user,
        )
        pending = EventBooking.objects.create(appointment=second.appointment)
        original_records = list(EventBooking.objects.values_list("pk", "status", "checked_in_at"))

        listing = self.client.get("/barangay/staff/events/?status=expired")
        history_url = f"/barangay/staff/events/{completed.pk}/participants/"
        self.assertContains(listing, history_url)
        history = self.client.get(history_url)
        self.assertEqual(history.status_code, 200)
        self.assertContains(history, completed.name)
        self.assertContains(history, "Covered Court")
        self.assertContains(history, "Total Registered")
        self.assertContains(history, "Scanned In")
        self.assertContains(history, "Not Yet Scanned")
        self.assertContains(history, "Scanned Resident")
        self.assertContains(history, "Pending Resident")
        self.assertNotContains(history, 'id="camera"')
        self.assertNotContains(history, 'id="manual-token"')
        self.assertEqual(history.context["history"]["stats"], {
            "registered": 2, "scanned": 1, "not_scanned": 1,
        })

        scanned_filter = self.client.get(history_url, {"status": "scanned"})
        self.assertContains(scanned_filter, "Scanned Resident")
        self.assertNotContains(scanned_filter, "Pending Resident")
        pending_filter = self.client.get(history_url, {"status": "not_scanned"})
        self.assertContains(pending_filter, "Pending Resident")
        self.assertNotContains(pending_filter, "Scanned Resident")
        search_result = self.client.get(history_url, {"q": "Scanned"})
        self.assertContains(search_result, "Scanned Resident")
        self.assertNotContains(search_result, "Pending Resident")

        self.assertEqual(self.client.get(f"/barangay/staff/events/{active.pk}/participants/").status_code, 404)
        active_scanner = self.client.get(f"/barangay/staff/events/scanner/?event={active.pk}")
        self.assertEqual(active_scanner.status_code, 200)
        self.assertContains(active_scanner, "Event QR Scanner")
        self.assertContains(active_scanner, 'id="camera"')

        other_barangay = Barangay.objects.create(
            name="History Other Barangay", address="Toledo City", contact_number="09660000000",
        )
        foreign = Service.objects.create(
            code="FHST", name="Foreign Completed History", description="Private",
            estimated_duration=15, is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT, barangay=other_barangay,
            event_start_date=today - timedelta(days=2), event_end_date=today - timedelta(days=1),
            booking_start_date=today - timedelta(days=8), booking_end_date=today - timedelta(days=3),
            capacity=20,
        )
        self.assertEqual(self.client.get(f"/barangay/staff/events/{foreign.pk}/participants/").status_code, 404)
        self.assertEqual(
            list(EventBooking.objects.values_list("pk", "status", "checked_in_at")),
            original_records,
        )
        scanned.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(scanned.status, EventBooking.Status.CHECKED_IN)
        self.assertEqual(pending.status, EventBooking.Status.CONFIRMED)

    def test_dashboard_priority_tasks_show_only_barangay_ready_documents_once(self):
        ready = self._ticket("priority-ready", "Ready", self.service, "D01")
        processing = self._ticket("priority-processing", "Processing", self.service, "D02")
        claimed = self._ticket("priority-claimed", "Claimed", self.service, "D03")
        foreign = self._ticket("priority-foreign", "Foreign", self.service, "D04")
        ready.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ready.save(update_fields=["claim_status", "updated_at"])
        processing.claim_status = QueueTicket.ClaimStatus.PROCESSING
        processing.save(update_fields=["claim_status", "updated_at"])
        claimed.claim_status = QueueTicket.ClaimStatus.CLAIMED
        claimed.save(update_fields=["claim_status", "updated_at"])
        foreign.claim_status = QueueTicket.ClaimStatus.READY
        foreign.save(update_fields=["claim_status", "updated_at"])
        other_barangay = Barangay.objects.create(
            name="Priority Task Other Barangay",
            address="Toledo City",
            contact_number="09770000000",
        )
        foreign.appointment.barangay = other_barangay
        foreign.appointment.save(update_fields=["barangay", "updated_at"])
        notification_count = Notification.objects.count()

        completion = self.client.post(
            f"/barangay/staff/documents/{ready.pk}/preview/",
            {"action": "complete"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(completion.status_code, 200)

        response = self.client.get("/barangay/staff/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([ticket.pk for ticket in response.context["ready_documents"]], [ready.pk])
        self.assertEqual(response.context["ready_count"], 1)
        content = response.content.decode()
        priority_section = content.split('<section class="priority"', 1)[1].split(
            '<section class="lower">', 1
        )[0]
        self.assertIn("Ready Resident", priority_section)
        self.assertIn(self.service.name, priority_section)
        self.assertIn("Ready for Pickup", priority_section)
        claim_link = f'/barangay/staff/dashboard/documents/{ready.pk}/claim/'
        self.assertContains(response, claim_link, count=1)
        self.assertContains(response, "Mark as Claimed")
        self.assertContains(response, "Mark Document as Claimed?")
        self.assertContains(response, "Are you sure this document has been claimed by the resident?")
        self.assertContains(response, "dashboard-action-icon", count=2)
        self.assertNotContains(response, "Open Document")
        self.assertContains(response, "/barangay/staff/documents/?status=R")
        self.assertNotIn("Processing Resident", priority_section)
        self.assertNotIn("Claimed Resident", priority_section)
        self.assertNotIn("Foreign Resident", priority_section)
        self.assertEqual(Notification.objects.count(), notification_count + 1)
        self.assertTrue(Notification.objects.filter(
            appointment=ready.appointment,
            notification_type=Notification.NotificationType.DOCUMENT_UPDATE,
            title="Document Ready for Pickup",
        ).exists())

    def test_dashboard_claim_action_is_locked_scoped_and_idempotent(self):
        ready = self._ticket("claim-ready", "Claim Ready", self.service, "D05")
        ready.claim_status = QueueTicket.ClaimStatus.READY
        ready.save(update_fields=["claim_status", "updated_at"])
        original_queue_status = ready.status
        original_appointment_status = ready.appointment.status
        notification_count = Notification.objects.count()
        claim_url = f"/barangay/staff/dashboard/documents/{ready.pk}/claim/"

        get_response = self.client.get(claim_url)
        self.assertEqual(get_response.status_code, 405)
        ready.refresh_from_db()
        self.assertEqual(ready.claim_status, QueueTicket.ClaimStatus.READY)

        claimed = self.client.post(claim_url, follow=True)
        self.assertRedirects(claimed, "/barangay/staff/dashboard/")
        self.assertContains(claimed, "was marked as claimed")
        ready.refresh_from_db()
        ready.appointment.refresh_from_db()
        self.assertEqual(ready.claim_status, QueueTicket.ClaimStatus.CLAIMED)
        self.assertIsNotNone(ready.claimed_at)
        self.assertEqual(ready.status, original_queue_status)
        self.assertEqual(ready.appointment.status, original_appointment_status)
        self.assertEqual(Notification.objects.count(), notification_count)
        claimed_priority = claimed.content.decode().split('<section class="priority"', 1)[1].split(
            '<section class="lower">', 1
        )[0]
        self.assertNotIn("Claim Ready Resident", claimed_priority)
        self.assertEqual(claimed.context["ready_count"], 0)

        completed = self.client.get("/barangay/staff/documents/?tab=completed")
        self.assertContains(completed, "Claim Ready Resident")

        claimed_at = ready.claimed_at
        repeated = self.client.post(claim_url, follow=True)
        self.assertContains(repeated, "Only documents that are ready for pickup")
        ready.refresh_from_db()
        self.assertEqual(ready.claim_status, QueueTicket.ClaimStatus.CLAIMED)
        self.assertEqual(ready.claimed_at, claimed_at)
        self.assertEqual(Notification.objects.count(), notification_count)

        foreign = self._ticket("claim-foreign", "Claim Foreign", self.service, "D06")
        foreign.claim_status = QueueTicket.ClaimStatus.READY
        foreign.save(update_fields=["claim_status", "updated_at"])
        other_barangay = Barangay.objects.create(
            name="Claim Other Barangay", address="Toledo City", contact_number="09550000000",
        )
        foreign.appointment.barangay = other_barangay
        foreign.appointment.save(update_fields=["barangay", "updated_at"])
        foreign_response = self.client.post(
            f"/barangay/staff/dashboard/documents/{foreign.pk}/claim/"
        )
        self.assertEqual(foreign_response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.claim_status, QueueTicket.ClaimStatus.READY)

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

    def test_staff_queue_uses_deterministic_estimated_time_as_queue_progresses(self):
        first = self._ticket("estimate-first", "First", self.service, "C01")
        second = self._ticket("estimate-second", "Second", self.service, "C02")
        url = f"/barangay/staff/queue/live/?slot={self.slot.pk}"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<small>Estimated Time</small>", html=True)
        self.assertNotContains(response, "AI Estimated Waiting Time")
        estimates = {ticket.pk: ticket.wait_minutes for ticket in response.context["tickets"]}
        self.assertEqual(estimates, {first.pk: 0, second.pk: self.service.estimated_duration})

        first.status = QueueTicket.Status.NOW_SERVING
        first.save(update_fields=["status", "updated_at"])
        serving_response = self.client.get(url)
        serving_estimates = {
            ticket.pk: ticket.wait_minutes for ticket in serving_response.context["tickets"]
        }
        self.assertEqual(serving_estimates[second.pk], self.service.estimated_duration)

        first.status = QueueTicket.Status.COMPLETED
        first.save(update_fields=["status", "updated_at"])
        completed_response = self.client.get(url)
        completed_estimates = {
            ticket.pk: ticket.wait_minutes for ticket in completed_response.context["tickets"]
        }
        self.assertEqual(completed_estimates[second.pk], 0)

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
        self.assertContains(response, 'class="logbook-table embedded-history-table"')
        self.assertContains(response, "COMPLETED SERVICE")
        self.assertContains(response, "COMPLETED DATE")

    def test_staff_appointment_tabs_have_the_requested_order_and_selection(self):
        response = self.client.get("/barangay/staff/appointments/?tab=rejected")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        tabs = content.split('<nav class="tabs">', 1)[1].split("</nav>", 1)[0]
        tab_labels = [
            "All Appointments",
            "Today",
            "Rejected / Cancelled",
            "Resident History",
        ]
        positions = [tabs.index(label) for label in tab_labels]
        self.assertEqual(positions, sorted(positions))
        self.assertContains(
            response,
            'class="active" href="?tab=rejected#appointment-list">Rejected / Cancelled</a>',
        )
        self.assertNotContains(response, "?tab=pending#appointment-list")

    def test_document_processing_action_still_updates_existing_ticket(self):
        ticket = self._ticket("document-resident", "Document", self.service, "C09")

        response = self.client.post(
            f"/barangay/staff/documents/{ticket.pk}/action/",
            {"action": "start"},
        )

        self.assertRedirects(response, "/barangay/staff/documents/", fetch_redirect_response=False)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)

    def test_documents_marks_only_overdue_unfinished_appointments_expired(self):
        today = timezone.localdate()
        expired = self._ticket("expired-document", "Expired", self.service, "X01")
        current = self._ticket("current-document", "Current", self.service, "X02")
        future = self._ticket("future-document", "Future", self.service, "X03")
        ready = self._ticket("ready-past-document", "Ready Past", self.service, "X04")
        claimed = self._ticket("claimed-past-document", "Claimed Past", self.service, "X05")
        completed = self._ticket("completed-past-document", "Completed Past", self.service, "X06")
        expired.appointment.appointment_date = today - timedelta(days=1)
        expired.appointment.save(update_fields=["appointment_date", "updated_at"])
        future.appointment.appointment_date = today + timedelta(days=1)
        future.appointment.save(update_fields=["appointment_date", "updated_at"])
        for protected in (ready, claimed, completed):
            protected.appointment.appointment_date = today - timedelta(days=1)
            protected.appointment.save(update_fields=["appointment_date", "updated_at"])
        ready.claim_status = QueueTicket.ClaimStatus.READY
        ready.save(update_fields=["claim_status", "updated_at"])
        claimed.claim_status = QueueTicket.ClaimStatus.CLAIMED
        claimed.save(update_fields=["claim_status", "updated_at"])
        completed.appointment.status = Appointment.Status.COMPLETED
        completed.appointment.save(update_fields=["status", "updated_at"])

        response = self.client.get("/barangay/staff/documents/")

        self.assertEqual(response.status_code, 200)
        tickets = {ticket.pk: ticket for ticket in response.context["tickets"]}
        self.assertTrue(tickets[expired.pk].is_expired)
        self.assertFalse(tickets[current.pk].is_expired)
        self.assertFalse(tickets[future.pk].is_expired)
        self.assertFalse(tickets[ready.pk].is_expired)
        self.assertFalse(tickets[completed.pk].is_expired)
        self.assertNotIn(claimed.pk, tickets)
        self.assertContains(response, '<b class="pill expired">Expired</b>', count=1)
        self.assertContains(response, "Archive Expired Appointment?")
        self.assertContains(
            response,
            "Are you sure you want to archive this expired appointment? Its records will remain available in history.",
        )
        self.assertContains(response, "Yes, Archive")

    def test_expired_document_archive_is_scoped_idempotent_and_notification_free(self):
        ticket = self._ticket("archive-expired", "Archive Expired", self.service, "X07")
        ticket.appointment.appointment_date = timezone.localdate() - timedelta(days=1)
        ticket.appointment.save(update_fields=["appointment_date", "updated_at"])
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        archive_url = f"/barangay/staff/documents/{ticket.pk}/action/"
        original_queue_status = ticket.status
        notification_count = Notification.objects.count()

        archived = self.client.post(archive_url, {"action": "archive_expired"}, follow=True)

        self.assertRedirects(archived, "/barangay/staff/documents/")
        self.assertContains(archived, "Archived expired appointment X07")
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.status, Appointment.Status.MISSED)
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)
        self.assertEqual(ticket.status, original_queue_status)
        self.assertEqual(Notification.objects.count(), notification_count)
        history = self.client.get("/barangay/staff/appointments/?tab=rejected")
        self.assertContains(history, "Archive Expired Resident")

        repeated = self.client.post(archive_url, {"action": "archive_expired"}, follow=True)
        self.assertContains(repeated, "Only overdue, unfinished appointments can be archived.")
        self.assertEqual(Notification.objects.count(), notification_count)

        ready = self._ticket("archive-ready", "Archive Ready", self.service, "X08")
        ready.appointment.appointment_date = timezone.localdate() - timedelta(days=1)
        ready.appointment.save(update_fields=["appointment_date", "updated_at"])
        ready.claim_status = QueueTicket.ClaimStatus.READY
        ready.save(update_fields=["claim_status", "updated_at"])
        protected = self.client.post(
            f"/barangay/staff/documents/{ready.pk}/action/",
            {"action": "archive_expired"},
            follow=True,
        )
        self.assertContains(protected, "Only overdue, unfinished appointments can be archived.")
        ready.refresh_from_db()
        ready.appointment.refresh_from_db()
        self.assertEqual(ready.claim_status, QueueTicket.ClaimStatus.READY)
        self.assertEqual(ready.appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(Notification.objects.count(), notification_count)
        legacy_archive = self.client.post(
            f"/barangay/staff/documents/{ready.pk}/action/",
            {"action": "archive"},
            follow=True,
        )
        self.assertContains(legacy_archive, "That document action is not available.")
        ready.refresh_from_db()
        self.assertEqual(ready.claim_status, QueueTicket.ClaimStatus.READY)
        self.assertEqual(Notification.objects.count(), notification_count)

        foreign = self._ticket("archive-foreign", "Archive Foreign", self.service, "X09")
        foreign.appointment.appointment_date = timezone.localdate() - timedelta(days=1)
        other_barangay = Barangay.objects.create(
            name="Archive Other Barangay", address="Toledo City", contact_number="09440000000",
        )
        foreign.appointment.barangay = other_barangay
        foreign.appointment.save(update_fields=["appointment_date", "barangay", "updated_at"])
        foreign_response = self.client.post(
            f"/barangay/staff/documents/{foreign.pk}/action/",
            {"action": "archive_expired"},
        )
        self.assertEqual(foreign_response.status_code, 404)
        foreign.appointment.refresh_from_db()
        self.assertEqual(foreign.appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(Notification.objects.count(), notification_count)

    def test_document_preview_actions_and_edit_use_latest_saved_details(self):
        ticket = self._ticket("preview-resident", "Preview", self.service, "C10")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        preview_url = f"/barangay/staff/documents/{ticket.pk}/preview/"

        preview = self.client.get(preview_url)

        self.assertEqual(preview.status_code, 200)
        for label in ("Edit", "Download", "Print", "Done"):
            self.assertContains(preview, label)
        self.assertContains(preview, "Appointment Information")
        self.assertContains(preview, 'class="edit-purpose"')
        self.assertContains(preview, 'class="done-action"')
        self.assertContains(preview, "Complete Document Processing?")
        self.assertContains(
            preview,
            "Are you done processing this document? It will be marked as Ready for Pickup.",
        )
        documents_page = self.client.get("/barangay/staff/documents/")
        self.assertNotContains(documents_page, 'class="edit-generated"')
        self.assertContains(documents_page, 'class="print-generated"')
        self.assertContains(documents_page, 'class="done-generated"')
        self.assertContains(documents_page, 'class="done-workflow"')
        self.assertNotContains(documents_page, "Complete &amp; Archive")
        self.assertContains(documents_page, "Complete Document Processing?")
        self.assertContains(documents_page, f"{preview_url}?embedded=1")

        edit = self.client.get(f"{preview_url}?embedded=1&edit=1")
        self.assertContains(edit, "Appointment Information")
        self.assertContains(edit, "Save")
        self.assertContains(edit, "Cancel")
        self.assertNotContains(edit, 'name="resident"')
        self.assertNotContains(edit, 'name="sitio"')

        original_status = ticket.claim_status
        saved = self.client.post(
            f"{preview_url}?embedded=1",
            {"purpose": "Updated employment requirement", "sitio": "Purok 7"},
        )

        self.assertRedirects(
            saved,
            f"{preview_url}?embedded=1",
            fetch_redirect_response=False,
        )
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.claim_status, original_status)
        self.assertEqual(ticket.appointment.purpose, "Updated employment requirement")
        self.assertNotEqual(ticket.appointment.sitio, "Purok 7")

        refreshed = self.client.get(preview_url)
        self.assertContains(refreshed, "Updated employment requirement")
        downloaded = self.client.get(f"{preview_url}?download=1")
        self.assertEqual(downloaded["Content-Type"], "text/plain")
        self.assertContains(downloaded, "Purpose: Updated employment requirement")
        self.assertContains(
            downloaded,
            f"Purok / Sitio: {ticket.appointment.sitio or 'Not provided'}",
        )
        printed = self.client.get(f"{preview_url}?print=1")
        self.assertContains(printed, "Updated employment requirement")
        self.assertContains(printed, "window.print()")

    def test_document_preview_rejects_invalid_edits_without_saving(self):
        ticket = self._ticket("invalid-preview", "Invalid", self.service, "C11")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        ticket.appointment.purpose = "Original purpose"
        ticket.appointment.sitio = "Original sitio"
        ticket.appointment.save(update_fields=["purpose", "sitio", "updated_at"])
        preview_url = f"/barangay/staff/documents/{ticket.pk}/preview/"

        response = self.client.post(
            preview_url,
            {"purpose": "x" * 501},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value has at most 500 characters")
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.purpose, "Original purpose")
        self.assertEqual(ticket.appointment.sitio, "Original sitio")

    def test_document_done_marks_ready_once_and_notifies_resident(self):
        ticket = self._ticket("done-preview", "Done", self.service, "C12")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        preview_url = f"/barangay/staff/documents/{ticket.pk}/preview/"
        appointment_status = ticket.appointment.status
        queue_status = ticket.status
        notification_count = Notification.objects.count()

        confirmation_page = self.client.get(preview_url)
        self.assertContains(confirmation_page, 'class="completion-no"')
        self.assertContains(confirmation_page, 'class="completion-yes"')
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)

        completed = self.client.post(
            preview_url,
            {"action": "complete"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(completed.status_code, 200)
        self.assertJSONEqual(
            completed.content,
            {"ok": True, "changed": True, "status": "ready"},
        )
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.READY)
        self.assertEqual(ticket.status, queue_status)
        self.assertEqual(ticket.appointment.status, appointment_status)
        self.assertEqual(Notification.objects.count(), notification_count + 1)
        notification = Notification.objects.get(
            appointment=ticket.appointment,
            notification_type=Notification.NotificationType.DOCUMENT_UPDATE,
        )
        self.assertEqual(notification.resident, ticket.appointment.resident)
        self.assertEqual(notification.recipient, ticket.appointment.resident.user)
        self.assertEqual(notification.barangay, self.barangay)
        self.assertEqual(notification.title, "Document Ready for Pickup")
        self.assertEqual(
            notification.message,
            "Your requested document has been processed and is now ready for pickup at your barangay office.",
        )
        self.assertFalse(notification.is_read)

        resident_client = APIClient()
        resident_client.force_authenticate(ticket.appointment.resident.user)
        notification_response = resident_client.get("/api/notifications/")
        self.assertEqual(notification_response.status_code, 200)
        self.assertEqual(notification_response.data["unread_count"], 1)
        self.assertEqual(notification_response.data["notifications"][0]["id"], notification.pk)

        other_ticket = self._ticket("notification-outsider", "Outsider", self.service, "C16")
        other_client = APIClient()
        other_client.force_authenticate(other_ticket.appointment.resident.user)
        other_response = other_client.get("/api/notifications/")
        self.assertEqual(other_response.status_code, 200)
        self.assertNotIn(
            notification.pk,
            {item["id"] for item in other_response.data["notifications"]},
        )

        repeated = self.client.post(
            preview_url,
            {"action": "complete"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(repeated.status_code, 200)
        self.assertJSONEqual(
            repeated.content,
            {"ok": True, "changed": False, "status": "ready"},
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.READY)
        self.assertEqual(Notification.objects.count(), notification_count + 1)

        ready_preview = self.client.get(preview_url)
        self.assertContains(ready_preview, "Ready for Pickup")
        self.assertContains(ready_preview, 'disabled aria-disabled="true"')

    @patch("qq.services.push_notifications._send_notification_push")
    def test_document_ready_push_is_queued_after_commit_for_configured_device(self, send_push):
        ticket = self._ticket("push-preview", "Push", self.service, "C14")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        PushDevice.objects.create(
            resident=ticket.appointment.resident,
            expo_push_token="ExponentPushToken[document-ready-test]",
            platform="android",
            is_active=True,
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/barangay/staff/documents/{ticket.pk}/preview/",
                {"action": "complete"},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        self.assertEqual(response.status_code, 200)
        notification = Notification.objects.get(
            appointment=ticket.appointment,
            notification_type=Notification.NotificationType.DOCUMENT_UPDATE,
        )
        send_push.assert_called_once_with(notification.pk)

    @patch("qq.services.push_notifications._send_notification_push", side_effect=RuntimeError("Expo unavailable"))
    def test_document_ready_push_failure_does_not_undo_completion(self, send_push):
        ticket = self._ticket("push-failure", "Push Failure", self.service, "C15")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/barangay/staff/documents/{ticket.pk}/preview/",
                {"action": "complete"},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.READY)
        self.assertTrue(Notification.objects.filter(appointment=ticket.appointment).exists())
        send_push.assert_called_once()

    def test_document_done_rejects_cross_barangay_attempt(self):
        ticket = self._ticket("foreign-document", "Foreign", self.service, "C13")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        other_barangay = Barangay.objects.create(
            name="Foreign Document Barangay",
            address="Toledo City",
            contact_number="09876543210",
        )
        ticket.appointment.barangay = other_barangay
        ticket.appointment.save(update_fields=["barangay", "updated_at"])

        response = self.client.post(
            f"/barangay/staff/documents/{ticket.pk}/preview/",
            {"action": "complete"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)
        self.assertFalse(Notification.objects.filter(appointment=ticket.appointment).exists())
