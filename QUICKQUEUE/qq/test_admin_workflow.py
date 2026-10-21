from datetime import date, datetime, time, timedelta
import io
import tempfile
import zipfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from qq.models import (
    Appointment, Barangay, BarangayStaff, DocumentTemplate, EventBooking,
    GeneratedDocument, Notification, QueueTicket, Resident, PushDevice, Service,
    ServiceWindow, TimeSlot,
)
from qq.services.queue_service import CHECKED_IN_NOTE


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
        self.staff = BarangayStaff.objects.create(
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

    def _ticket(self, username, first_name, service, queue_number, *, checked_in=False):
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
        return QueueTicket.objects.create(
            appointment=appointment,
            queue_number=queue_number,
            served_by=self.staff,
            notes=CHECKED_IN_NOTE if checked_in else "",
        )

    @staticmethod
    def _placeholder_docx():
        document_xml = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Resident: {{ resident_</w:t></w:r>
          <w:r><w:t>full_name }} / {{ purpose }} / {{ resident_middle_name }} / {{ official_signature }}</w:t></w:r></w:p></w:body>
        </w:document>'''
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as package:
            package.writestr("word/document.xml", document_xml)
            package.writestr("word/media/seal.png", b"official-seal-bytes")
        return stream.getvalue()

    @staticmethod
    def _plain_docx():
        document_xml = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>Resident information must be verified by staff.</w:t></w:r></w:p></w:body>
        </w:document>'''
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as package:
            package.writestr("word/document.xml", document_xml)
        return stream.getvalue()

    def test_staff_generates_populated_docx_without_changing_template_or_lifecycle(self):
        ticket = self._ticket("generated-resident", "Generated", self.service, "C20")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        ticket.appointment.purpose = "Employment requirement"
        ticket.appointment.save(update_fields=["purpose", "updated_at"])

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            template = DocumentTemplate.objects.create(
                barangay=self.barangay,
                service=self.service,
                name="Clearance Placeholder Template",
                template_file=SimpleUploadedFile(
                    "clearance.docx",
                    self._placeholder_docx(),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
                uploaded_by=self.admin_user,
            )
            with template.template_file.open("rb") as source:
                original = source.read()

            preview_url = f"/barangay/staff/documents/{ticket.pk}/preview/"
            preview = self.client.get(preview_url)
            self.assertContains(preview, "Clearance Placeholder Template")
            self.assertContains(preview, "Generate Document")

            generated_response = self.client.post(
                preview_url,
                {"action": "generate"},
                follow=True,
            )
            self.assertContains(generated_response, "Generated DOC-")
            generated = GeneratedDocument.objects.get(ticket=ticket)
            with generated.document_file.open("rb") as output:
                generated_bytes = output.read()
            with zipfile.ZipFile(io.BytesIO(generated_bytes)) as package:
                generated_xml = package.read("word/document.xml").decode()
                self.assertEqual(package.read("word/media/seal.png"), b"official-seal-bytes")
            self.assertIn("Generated Resident", generated_xml)
            self.assertIn("Employment requirement", generated_xml)
            self.assertNotIn("resident_full_name", generated_xml)
            self.assertIn("resident_middle_name", generated_xml)
            self.assertIn("official_signature", generated_xml)
            self.assertIn("<ns0:b", generated_xml)

            with template.template_file.open("rb") as source:
                self.assertEqual(source.read(), original)
            ticket.refresh_from_db()
            self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)

            download = self.client.get(f"{preview_url}?download=1")
            self.assertEqual(
                download["Content-Type"],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            self.assertIn(".docx", download["Content-Disposition"])
            download.close()

    def test_template_without_placeholders_is_not_generated_or_marked_ready(self):
        ticket = self._ticket("plain-template", "Plain", self.other_service, "C21")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            DocumentTemplate.objects.create(
                barangay=self.barangay,
                service=self.other_service,
                name="Plain Official Template",
                template_file=SimpleUploadedFile("plain.docx", self._plain_docx()),
                uploaded_by=self.admin_user,
            )
            response = self.client.post(
                f"/barangay/staff/documents/{ticket.pk}/preview/",
                {"action": "generate"},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("no recognized", response.json()["error"])
        self.assertFalse(GeneratedDocument.objects.filter(ticket=ticket).exists())
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)

    def test_generated_document_storage_failure_is_reported_without_ready_transition(self):
        ticket = self._ticket("generation-failure", "Failure", self.service, "C22")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            DocumentTemplate.objects.create(
                barangay=self.barangay,
                service=self.service,
                name="Storage Failure Template",
                template_file=SimpleUploadedFile("failure.docx", self._placeholder_docx()),
                uploaded_by=self.admin_user,
            )
            with patch(
                "django.db.models.fields.files.FieldFile.save",
                side_effect=OSError("storage unavailable"),
            ):
                response = self.client.post(
                    f"/barangay/staff/documents/{ticket.pk}/preview/",
                    {"action": "generate"},
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("persistent storage", response.json()["error"])
        self.assertFalse(GeneratedDocument.objects.filter(ticket=ticket).exists())
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)

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

    def test_staff_notification_read_state_is_recipient_scoped_across_portal_pages(self):
        notification = Notification.objects.create(
            recipient=self.staff_user,
            recipient_role=Notification.RecipientRole.STAFF,
            barangay=self.barangay,
            notification_type=Notification.NotificationType.STAFF_ALERT,
            title="Staff workflow alert",
            message="A test notification for this staff account.",
        )
        other_user = User.objects.create_user(username="notification-other-staff", password="secret")
        BarangayStaff.objects.create(
            barangay=self.barangay,
            user=other_user,
            first_name="Other",
            last_name="Staff",
            username="notification-other-staff",
            role=BarangayStaff.Role.STAFF,
        )
        other_notification = Notification.objects.create(
            recipient=other_user,
            recipient_role=Notification.RecipientRole.STAFF,
            barangay=self.barangay,
            notification_type=Notification.NotificationType.STAFF_ALERT,
            title="Other staff alert",
            message="This notification must remain private.",
        )
        portal_urls = (
            "/barangay/staff/dashboard/",
            "/barangay/staff/appointments/",
            "/barangay/staff/queue/live/",
            "/barangay/staff/documents/",
            "/barangay/staff/events/",
            "/barangay/staff/events/scanner/",
            "/barangay/staff/settings/",
        )

        for url in portal_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(response.context["unread_notifications"], 1, url)
            bell_markup = response.content.decode().split('class="bell"', 1)[1].split("</a>", 1)[0]
            self.assertIn("<i></i>", bell_markup, url)

        forbidden = self.client.post(
            "/barangay/notifications/",
            data={"notification_id": other_notification.pk},
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(forbidden.status_code, 200)
        self.assertJSONEqual(forbidden.content, {"updated": 0, "unread_count": 1})
        other_notification.refresh_from_db()
        self.assertFalse(other_notification.is_read)

        marked = self.client.post(
            "/barangay/notifications/",
            data={"notification_id": notification.pk},
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(marked.status_code, 200)
        self.assertJSONEqual(marked.content, {"updated": 1, "unread_count": 0})
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

        for url in portal_urls:
            response = self.client.get(url)
            self.assertEqual(response.context["unread_notifications"], 0, url)
            bell_markup = response.content.decode().split('class="bell"', 1)[1].split("</a>", 1)[0]
            self.assertNotIn("<i></i>", bell_markup, url)

        Notification.objects.create(
            recipient=self.staff_user,
            recipient_role=Notification.RecipientRole.STAFF,
            barangay=self.barangay,
            notification_type=Notification.NotificationType.STAFF_ALERT,
            title="New staff alert",
            message="A newly unread notification.",
        )
        refreshed = self.client.get("/barangay/staff/settings/")
        self.assertEqual(refreshed.context["unread_notifications"], 1)
        bell_markup = refreshed.content.decode().split('class="bell"', 1)[1].split("</a>", 1)[0]
        self.assertIn("<i></i>", bell_markup)

    def test_staff_notification_dropdown_compact_and_expanded_history_are_scoped(self):
        Notification.objects.bulk_create([
            Notification(
                recipient=self.staff_user,
                recipient_role=Notification.RecipientRole.STAFF,
                barangay=self.barangay,
                notification_type=Notification.NotificationType.STAFF_ALERT,
                title=f"Staff history {index}",
                message=f"Notification history item {index}",
                event_key=f"staff-dropdown:{self.staff_user.pk}:{index}",
            )
            for index in range(55)
        ])
        other_user = User.objects.create_user(username="dropdown-other", password="secret")
        BarangayStaff.objects.create(
            barangay=self.barangay,
            user=other_user,
            first_name="Dropdown",
            last_name="Other",
            username="dropdown-other",
            role=BarangayStaff.Role.STAFF,
        )
        Notification.objects.create(
            recipient=other_user,
            recipient_role=Notification.RecipientRole.STAFF,
            barangay=self.barangay,
            notification_type=Notification.NotificationType.STAFF_ALERT,
            title="Private other-staff notification",
            message="Must never enter this staff member's dropdown.",
            event_key=f"staff-dropdown:{other_user.pk}:private",
        )

        compact = self.client.get(
            "/barangay/notifications/?format=json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(compact.status_code, 200)
        self.assertEqual(compact.json()["total_count"], 55)
        self.assertEqual(compact.json()["unread_count"], 55)
        self.assertEqual(len(compact.json()["notifications"]), 6)
        self.assertNotContains(compact, "Private other-staff notification")

        expanded_first = self.client.get(
            "/barangay/notifications/?format=json&expanded=1&page=1",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(len(expanded_first.json()["notifications"]), 50)
        self.assertEqual(expanded_first.json()["page_count"], 2)
        self.assertTrue(expanded_first.json()["has_next"])
        expanded_second = self.client.get(
            "/barangay/notifications/?format=json&expanded=1&page=2",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(len(expanded_second.json()["notifications"]), 5)
        self.assertFalse(expanded_second.json()["has_next"])
        self.assertEqual(
            Notification.objects.filter(recipient=self.staff_user, is_read=False).count(),
            55,
        )

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
        self.assertContains(response, 'class="event-row-icon"')
        self.assertContains(response, '<svg viewBox="0 0 24 24">')
        self.assertNotContains(response, "◇")
        self.assertContains(response, "Upcoming")
        self.assertNotContains(response, "Other Barangay Private Event")
        self.assertNotContains(response, "Expired Staff Event")

    def test_special_service_registrations_are_isolated_from_regular_staff_workflows(self):
        today = timezone.localdate()
        regular_ticket = self._ticket(
            "regular-isolation", "Regular Isolation", self.service, "C17", checked_in=True
        )
        special_service = Service.objects.create(
            code="EVS",
            name="Isolated Community Event",
            description="Managed only through Events & Temporary Services",
            estimated_duration=15,
            is_temporary=True,
            temporary_type=Service.TemporaryType.EVENT,
            barangay=self.barangay,
            event_start_date=today,
            event_end_date=today + timedelta(days=1),
            booking_start_date=today - timedelta(days=1),
            booking_end_date=today,
            capacity=20,
        )
        event_ticket = self._ticket(
            "event-isolation", "Event Isolation", special_service, "EV17", checked_in=True
        )
        event_booking = EventBooking.objects.create(appointment=event_ticket.appointment)
        event_ticket.appointment.status = Appointment.Status.PENDING
        event_ticket.appointment.save(update_fields=["status", "updated_at"])
        event_ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        event_ticket.save(update_fields=["claim_status", "updated_at"])

        admin_client = APIClient()
        admin_client.force_login(self.admin_user)
        special_appointments = admin_client.get(
            "/barangay/appointments/",
            {"special_q": event_booking.booking_reference},
        )
        self.assertEqual(special_appointments.status_code, 200)
        special_section = special_appointments.content.decode().split(
            'id="special-services"', 1
        )[1]
        self.assertIn("Booking Reference", special_section)
        self.assertIn(event_booking.booking_reference, special_section)
        self.assertNotIn("Queue No.", special_section)

        before_slot_end = timezone.make_aware(datetime.combine(today, time(8, 30)))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            appointments = self.client.get(
                f"/barangay/staff/appointments/?date={today.isoformat()}"
            )
        self.assertEqual(appointments.context["today_total"], 1)
        self.assertEqual(appointments.context["selected_count"], 1)
        self.assertEqual(
            list(appointments.context["appointments"].values_list("pk", flat=True)),
            [regular_ticket.appointment_id],
        )
        self.assertNotContains(appointments, special_service.name)

        dashboard = self.client.get("/barangay/staff/dashboard/")
        self.assertEqual(dashboard.context["pending_appointments"], 0)
        self.assertEqual(dashboard.context["processing_documents"], 0)
        self.assertContains(dashboard, special_service.name)
        self.assertNotIn(event_ticket, dashboard.context["waiting_tickets"])

        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            live_queue = self.client.get(
                f"/barangay/staff/queue/live/?slot={self.slot.pk}"
            )
        self.assertEqual(
            [ticket.pk for ticket in live_queue.context["tickets"]],
            [regular_ticket.pk],
        )
        self.assertNotContains(live_queue, special_service.name)

        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            documents = self.client.get("/barangay/staff/documents/")
        self.assertEqual(documents.context["processing_count"], 0)
        self.assertNotContains(documents, special_service.name)
        blocked_preview = self.client.get(
            f"/barangay/staff/documents/{event_ticket.pk}/preview/"
        )
        self.assertEqual(blocked_preview.status_code, 404)

        events = self.client.get("/barangay/staff/events/")
        self.assertContains(events, special_service.name)
        attendance = self.client.get(
            f"/barangay/staff/events/scanner/?event={special_service.pk}&format=json"
        )
        self.assertEqual(attendance.status_code, 200)
        self.assertEqual(attendance.json()["stats"]["registered"], 1)
        self.assertEqual(attendance.json()["participants"][0]["booking_reference"], event_booking.booking_reference)

        now = timezone.now()
        regular_ticket.claim_status = QueueTicket.ClaimStatus.CLAIMED
        regular_ticket.claimed_at = now
        regular_ticket.save(update_fields=["claim_status", "claimed_at", "updated_at"])
        event_ticket.claim_status = QueueTicket.ClaimStatus.CLAIMED
        event_ticket.claimed_at = now
        event_ticket.save(update_fields=["claim_status", "claimed_at", "updated_at"])
        history = self.client.get("/barangay/staff/appointments/?tab=history")
        resident_rows = history.context["resident_rows"]
        self.assertEqual([row["latest"].pk for row in resident_rows], [regular_ticket.pk])
        self.assertNotContains(history, special_service.name)

        blocked_review = self.client.post(
            f"/barangay/staff/appointments/{event_ticket.appointment_id}/review/",
            {"decision": "approve"},
        )
        self.assertEqual(blocked_review.status_code, 404)
        event_ticket.appointment.refresh_from_db()
        self.assertEqual(event_ticket.appointment.status, Appointment.Status.PENDING)

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

    def test_counter_completion_ready_and_claim_follow_single_consistent_lifecycle(self):
        window = ServiceWindow.objects.create(
            barangay=self.barangay,
            number=1,
            name="Window 1",
            assigned_staff=self.staff,
        )
        ticket = self._ticket(
            "lifecycle-resident", "Lifecycle", self.service, "L01", checked_in=True
        )
        ticket.status = QueueTicket.Status.NOW_SERVING
        ticket.service_window = window
        ticket.save(update_fields=["status", "service_window", "updated_at"])
        ticket.appointment.status = Appointment.Status.ONGOING
        ticket.appointment.save(update_fields=["status", "updated_at"])

        counter_done = self.client.post(f"/barangay/queue/{ticket.pk}/complete/")
        self.assertEqual(counter_done.status_code, 302)
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.COMPLETED)
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)
        self.assertEqual(ticket.appointment.status, Appointment.Status.ONGOING)
        self.assertEqual(ticket.appointment.workflow_status_display, "Processing")

        dashboard = self.client.get("/barangay/staff/dashboard/")
        self.assertEqual(dashboard.context["processing_documents"], 1)
        self.assertIsNone(dashboard.context["now_serving"])

        ready = self.client.post(
            f"/barangay/staff/documents/{ticket.pk}/preview/",
            {"action": "complete"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(ready.status_code, 200)
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.READY)
        self.assertEqual(ticket.appointment.status, Appointment.Status.ONGOING)
        self.assertEqual(ticket.appointment.workflow_status_display, "Ready for Pickup")
        self.assertEqual(
            self.client.get("/barangay/staff/dashboard/").context["processing_documents"],
            0,
        )

        resident_client = APIClient()
        resident_client.force_authenticate(ticket.appointment.resident.user)
        self.assertEqual(
            resident_client.get("/api/queue-status/").data["appointment"]["status"],
            "Ready for Pickup",
        )

        claimed = self.client.post(
            f"/barangay/staff/dashboard/documents/{ticket.pk}/claim/"
        )
        self.assertEqual(claimed.status_code, 302)
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.CLAIMED)
        self.assertEqual(ticket.appointment.status, Appointment.Status.COMPLETED)
        self.assertIsNone(
            resident_client.get("/api/queue-status/").data["appointment"]
        )

        admin_client = APIClient()
        admin_client.force_login(self.admin_user)
        # A legacy stale queue value must not override the finalized claim and
        # appointment state or put the resident back into an active queue.
        QueueTicket.objects.filter(pk=ticket.pk).update(
            status=QueueTicket.Status.NOW_SERVING
        )
        admin_dashboard = admin_client.get("/barangay/dashboard/")
        self.assertIsNone(admin_dashboard.context["now_serving"])
        self.assertEqual(admin_dashboard.context["completed"], 1)
        self.assertEqual(admin_dashboard.context["serving_count"], 0)
        activity = admin_dashboard.content.decode().split(
            "Recent Queue Activity", 1
        )[1].split("Live Queue Monitor", 1)[0]
        self.assertIn("Completed", activity)
        self.assertIn("activity-status-icon", activity)
        self.assertNotIn("Now Serving", activity)

        admin_monitor = admin_client.get(
            f"/barangay/queue/live/?slot={self.slot.pk}"
        )
        self.assertIsNone(admin_monitor.context["now_serving"])
        self.assertEqual(admin_monitor.context["completed_count"], 1)

        self.client.force_login(self.staff_user)
        staff_queue = self.client.get(
            f"/barangay/staff/queue/live/?slot={self.slot.pk}"
        )
        self.assertIsNone(staff_queue.context["now_serving"])
        self.assertEqual(staff_queue.context["completed_count"], 1)

        admin_appointments = admin_client.get("/barangay/appointments/")
        self.assertContains(admin_appointments, "status-completed")
        self.assertContains(admin_appointments, ">Completed</span>")

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
        self.assertNotContains(response, 'class="count"')
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
        ready.status = QueueTicket.Status.NOW_SERVING
        ready.notes = CHECKED_IN_NOTE
        ready.save(update_fields=["claim_status", "status", "notes", "updated_at"])
        ready.appointment.status = Appointment.Status.ONGOING
        ready.appointment.save(update_fields=["status", "updated_at"])
        notification_count = Notification.objects.count()
        claim_url = f"/barangay/staff/dashboard/documents/{ready.pk}/claim/"

        staff_queue_before = self.client.get(
            f"/barangay/staff/queue/live/?slot={self.slot.pk}"
        )
        self.assertIn(ready.pk, [item.pk for item in staff_queue_before.context["tickets"]])

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
        self.assertEqual(ready.status, QueueTicket.Status.COMPLETED)
        self.assertEqual(ready.appointment.status, Appointment.Status.COMPLETED)
        self.assertEqual(Notification.objects.count(), notification_count + 1)
        staff_queue_after = self.client.get(
            f"/barangay/staff/queue/live/?slot={self.slot.pk}"
        )
        self.assertNotIn(ready.pk, [item.pk for item in staff_queue_after.context["tickets"]])
        admin_client = APIClient()
        admin_client.force_login(self.admin_user)
        admin_monitor = admin_client.get(f"/barangay/queue/live/?slot={self.slot.pk}")
        self.assertNotIn(ready.pk, [item.pk for item in admin_monitor.context["tickets"]])
        self.assertIsNone(admin_monitor.context["now_serving"])
        admin_dashboard = admin_client.get("/barangay/dashboard/")
        self.assertIsNone(admin_dashboard.context["now_serving"])
        resident_client = APIClient()
        resident_client.force_authenticate(ready.appointment.resident.user)
        self.assertIsNone(resident_client.get("/api/queue-status/").data["appointment"])
        history = resident_client.get("/api/transactions/")
        claimed_record = next(item for item in history.data["transactions"] if item["id"] == ready.appointment_id)
        self.assertEqual(claimed_record["status_code"], Appointment.Status.COMPLETED)
        self.assertIsNotNone(claimed_record["date_claimed"])
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
        self.assertEqual(Notification.objects.count(), notification_count + 1)

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
        matching = self._ticket("ana", "Ana", self.service, "C01", checked_in=True)
        self._ticket("ben", "Ben", self.other_service, "I01", checked_in=True)

        response = self.client.get(
            f"/barangay/staff/queue/live/?slot={self.slot.pk}&q=Ana&service={self.service.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([ticket.pk for ticket in response.context["tickets"]], [matching.pk])
        self.assertEqual(response.context["filters"], {"q": "Ana", "service": str(self.service.pk)})

    def test_staff_queue_uses_deterministic_estimated_time_as_queue_progresses(self):
        first = self._ticket("estimate-first", "First", self.service, "C01", checked_in=True)
        second = self._ticket("estimate-second", "Second", self.service, "C02", checked_in=True)
        url = f"/barangay/staff/queue/live/?slot={self.slot.pk}"
        before_slot_end = timezone.make_aware(datetime.combine(
            first.appointment.appointment_date, time(8, 30),
        ))

        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<small>Estimated Time</small>", html=True)
        self.assertNotContains(response, "AI Estimated Waiting Time")
        estimates = {ticket.pk: ticket.wait_minutes for ticket in response.context["tickets"]}
        self.assertEqual(estimates, {first.pk: 0, second.pk: self.service.estimated_duration})

        first.status = QueueTicket.Status.NOW_SERVING
        first.save(update_fields=["status", "updated_at"])
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            serving_response = self.client.get(url)
        serving_estimates = {
            ticket.pk: ticket.wait_minutes for ticket in serving_response.context["tickets"]
        }
        self.assertEqual(serving_estimates[second.pk], self.service.estimated_duration)
        table_markup = serving_response.content.decode().split(
            '<section class="queue-table panel">', 1
        )[1].split("</section>", 1)[0]
        self.assertIn(">Skip</button>", table_markup)
        self.assertIn(">Serve Now</button>", table_markup)
        self.assertNotIn(">Complete</button>", table_markup)
        self.assertContains(
            serving_response,
            "font:700 11px Poppins,Arial,sans-serif",
        )

        first.status = QueueTicket.Status.COMPLETED
        first.save(update_fields=["status", "updated_at"])
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
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

    def test_admin_live_monitor_shows_only_checked_in_regular_queue_tickets(self):
        checked_in = self._ticket(
            "monitor-checked", "Checked", self.service, "C10", checked_in=True
        )
        unchecked = self._ticket("monitor-booked", "Booked", self.service, "C11")
        temporary_service = Service.objects.create(
            code="EVT-MON",
            name="Monitor Event",
            description="Event registrations stay outside the regular queue.",
            estimated_duration=15,
            is_temporary=True,
            barangay=self.barangay,
            event_start_date=timezone.localdate(),
            event_end_date=timezone.localdate(),
        )
        event_ticket = self._ticket(
            "monitor-event", "Event", temporary_service, "E10", checked_in=True
        )
        other_barangay = Barangay.objects.create(
            name="Foreign Monitor Barangay",
            address="Toledo City",
            contact_number="09128888888",
        )
        other_slot = TimeSlot.objects.create(
            barangay=other_barangay,
            start_time=time(8),
            end_time=time(9),
            max_appointments=5,
        )
        other_user = User.objects.create_user("foreign-monitor", password="secret")
        other_resident = Resident.objects.create(
            user=other_user,
            first_name="Foreign",
            last_name="Monitor",
            birthdate=date(2000, 1, 1),
            sex=Resident.Sex.MALE,
            contact_number="09128888889",
            barangay=other_barangay,
        )
        other_appointment = Appointment.objects.create(
            resident=other_resident,
            barangay=other_barangay,
            service=self.service,
            appointment_date=timezone.localdate(),
            time_slot=other_slot,
            queue_number="F10",
            status=Appointment.Status.CONFIRMED,
        )
        QueueTicket.objects.create(
            appointment=other_appointment,
            queue_number="F10",
            notes=CHECKED_IN_NOTE,
        )
        self.client.force_login(self.admin_user)

        before_slot_end = timezone.make_aware(datetime.combine(
            timezone.localdate(), time(8, 30),
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            response = self.client.get(f"/barangay/queue/live/?slot={self.slot.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([ticket.pk for ticket in response.context["tickets"]], [checked_in.pk])
        self.assertContains(response, "Checked Resident")
        self.assertContains(response, "8:00 AM")
        self.assertContains(response, "Waiting")
        self.assertNotContains(response, unchecked.queue_number)
        self.assertNotContains(response, event_ticket.queue_number)
        self.assertNotContains(response, "Foreign Monitor")
        self.assertNotContains(response, "Call Next")
        self.assertNotContains(response, ">Complete<")
        self.assertNotContains(response, ">Skip<")
        self.assertContains(response, "Read-only monitor")
        self.assertContains(response, "qq/js/barangay_live_queue.js")

    def test_admin_monitor_tracks_staff_status_and_assigned_window(self):
        window = ServiceWindow.objects.create(
            barangay=self.barangay,
            number=2,
            name="Window 2",
            assigned_staff=self.staff,
        )
        ticket = self._ticket(
            "monitor-serving", "Serving", self.service, "C12", checked_in=True
        )
        before_slot_end = timezone.make_aware(datetime.combine(
            timezone.localdate(), time(8, 30),
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            called = self.client.post("/barangay/queue/call-next/", {"slot": self.slot.pk})
        self.assertRedirects(
            called,
            f"/barangay/staff/queue/live/?slot={self.slot.pk}",
            fetch_redirect_response=False,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.NOW_SERVING)
        self.assertEqual(ticket.service_window_id, window.pk)
        self.client.force_login(self.admin_user)

        response = self.client.get(f"/barangay/queue/live/?slot={self.slot.pk}")

        self.assertEqual(response.context["now_serving"].pk, ticket.pk)
        self.assertContains(response, "Serving Resident")
        self.assertContains(response, "Window 2")
        self.assertContains(response, "Now Serving")
        self.assertContains(response, 'class="assigned-window-value"')

        forbidden = self.client.post("/barangay/queue/skip/", {"slot": self.slot.pk})
        self.assertEqual(forbidden.status_code, 403)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, QueueTicket.Status.NOW_SERVING)

    def test_resident_check_in_is_idempotent_and_activates_existing_ticket(self):
        ticket = self._ticket("monitor-resident", "Mobile", self.service, "C13")
        resident_client = APIClient()
        resident_client.force_authenticate(ticket.appointment.resident.user)

        before_slot_end = timezone.make_aware(datetime.combine(
            ticket.appointment.appointment_date, time(8, 30),
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            first = resident_client.post(
                "/api/queue-status/",
                {"appointment_id": ticket.appointment_id, "action": "check_in"},
                format="json",
            )
            second = resident_client.post(
                "/api/queue-status/",
                {"appointment_id": ticket.appointment_id, "action": "check_in"},
                format="json",
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(first.data["changed"])
        self.assertTrue(first.data["checked_in"])
        self.assertTrue(first.data["staff_notification_created"])
        self.assertFalse(second.data["changed"])
        self.assertTrue(second.data["checked_in"])
        self.assertEqual(
            Notification.objects.filter(
                appointment=ticket.appointment,
                title="Resident Checked In",
            ).count(),
            1,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.notes, CHECKED_IN_NOTE)
        at_slot_end = timezone.make_aware(datetime.combine(
            ticket.appointment.appointment_date, self.slot.end_time,
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=at_slot_end):
            status_response = resident_client.get("/api/queue-status/")
        self.assertTrue(status_response.data["appointment"]["checked_in"])
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.status, Appointment.Status.CONFIRMED)
        self.client.force_login(self.admin_user)
        with patch("qq.services.appointment_expiration.timezone.now", return_value=at_slot_end):
            monitor = self.client.get(f"/barangay/queue/live/?slot={self.slot.pk}")
        self.assertEqual([item.pk for item in monitor.context["tickets"]], [ticket.pk])

    def test_resident_check_in_before_slot_start_is_rejected(self):
        ticket = self._ticket("early-check-in", "Early", self.service, "C15")
        resident_client = APIClient()
        resident_client.force_authenticate(ticket.appointment.resident.user)
        before_slot_start = timezone.make_aware(datetime.combine(
            ticket.appointment.appointment_date, time(7, 59),
        ))

        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_start):
            response = resident_client.post(
                "/api/queue-status/",
                {"appointment_id": ticket.appointment_id, "action": "check_in"},
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        ticket.refresh_from_db()
        self.assertEqual(ticket.notes, "")
        self.assertEqual(ticket.appointment.status, Appointment.Status.CONFIRMED)

    def test_unchecked_resident_expires_at_slot_end_and_cannot_check_in(self):
        for suffix, minute in (("exact", 0), ("late", 1)):
            with self.subTest(boundary=suffix):
                ticket = self._ticket(
                    f"expiry-check-in-{suffix}", "Expiry", self.service,
                    f"C{16 + minute}",
                )
                resident_client = APIClient()
                resident_client.force_authenticate(ticket.appointment.resident.user)
                at_or_after_end = timezone.make_aware(datetime.combine(
                    ticket.appointment.appointment_date, self.slot.end_time,
                )) + timedelta(minutes=minute)

                with patch("qq.services.appointment_expiration.timezone.now", return_value=at_or_after_end):
                    response = resident_client.post(
                        "/api/queue-status/",
                        {"appointment_id": ticket.appointment_id, "action": "check_in"},
                        format="json",
                    )
                    queue_status = resident_client.get("/api/queue-status/")
                    transactions = resident_client.get("/api/transactions/")

                self.assertEqual(response.status_code, 400)
                self.assertIsNone(queue_status.data["appointment"])
                transaction = next(
                    item for item in transactions.data["transactions"]
                    if item["id"] == ticket.appointment_id
                )
                self.assertEqual(transaction["status_code"], Appointment.Status.MISSED)
                ticket.refresh_from_db()
                ticket.appointment.refresh_from_db()
                self.assertEqual(ticket.appointment.status, Appointment.Status.MISSED)
                self.assertEqual(ticket.status, QueueTicket.Status.MISSED)

    def test_staff_documents_are_consolidated_with_processing_and_completed_tabs(self):
        today = timezone.localdate()
        before_slot_end = timezone.make_aware(datetime.combine(today, time(8, 30)))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
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
        summary = content.split('<section class="summary">', 1)[1].split("</section>", 1)[0]
        self.assertEqual(summary.count("<article>"), 3)
        self.assertNotIn("Needs Attention", summary)
        summary_labels = ["Appointments Today", "Confirmed", "Tomorrow"]
        summary_positions = [summary.index(label) for label in summary_labels]
        self.assertEqual(summary_positions, sorted(summary_positions))
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

    def test_staff_appointment_lists_label_slot_expiry_without_relabeling_no_shows(self):
        expired = self._ticket("staff-expired-label", "Expired", self.service, "E01")
        missed = self._ticket("staff-missed-label", "Missed", self.service, "M01")
        missed.appointment.status = Appointment.Status.MISSED
        missed.appointment.save(update_fields=["status", "updated_at"])
        missed.status = QueueTicket.Status.MISSED
        missed.notes = "Resident did not show up"
        missed.save(update_fields=["status", "notes", "updated_at"])
        rejected = self._ticket("staff-rejected-label", "Rejected", self.service, "R01")
        rejected.appointment.status = Appointment.Status.CANCELLED
        rejected.appointment.save(update_fields=["status", "updated_at"])
        rejected.status = QueueTicket.Status.CANCELLED
        rejected.save(update_fields=["status", "updated_at"])

        at_slot_end = timezone.make_aware(datetime.combine(
            expired.appointment.appointment_date, self.slot.end_time,
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=at_slot_end):
            all_appointments = self.client.get("/barangay/staff/appointments/?tab=all")
            rejected_tab = self.client.get("/barangay/staff/appointments/?tab=rejected")

        self.assertEqual(all_appointments.status_code, 200)
        self.assertEqual(rejected_tab.status_code, 200)
        all_statuses = {
            item.pk: item.portal_status_display
            for item in all_appointments.context["appointments"]
        }
        selected_statuses = {
            item.pk: item.portal_status_display
            for item in all_appointments.context["selected_appointments"]
        }
        rejected_statuses = {
            item.pk: item.portal_status_display
            for item in rejected_tab.context["appointments"]
        }
        self.assertEqual(all_statuses[expired.appointment_id], "Expired")
        self.assertEqual(selected_statuses[expired.appointment_id], "Expired")
        self.assertEqual(rejected_statuses[expired.appointment_id], "Expired")
        self.assertEqual(rejected_statuses[missed.appointment_id], "Missed")
        self.assertEqual(rejected_statuses[rejected.appointment_id], "Cancelled")
        self.assertContains(all_appointments, "Expired")
        self.assertContains(rejected_tab, "Expired")
        self.assertContains(rejected_tab, "Missed")
        self.assertContains(rejected_tab, "Cancelled")

    def test_document_processing_action_still_updates_existing_ticket(self):
        ticket = self._ticket("document-resident", "Document", self.service, "C09")
        before_slot_end = timezone.make_aware(datetime.combine(
            ticket.appointment.appointment_date, time(8, 59),
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
            response = self.client.post(
                f"/barangay/staff/documents/{ticket.pk}/action/",
                {"action": "start"},
            )

        self.assertRedirects(response, "/barangay/staff/documents/", fetch_redirect_response=False)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)

    def test_document_start_is_available_to_unassigned_confirmed_ticket_and_assigns_staff(self):
        ticket = self._ticket("unassigned-document", "Unassigned", self.service, "C11")
        ticket.served_by = None
        ticket.save(update_fields=["served_by", "updated_at"])
        slot_start = timezone.make_aware(datetime.combine(
            ticket.appointment.appointment_date, time(8, 59),
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=slot_start):
            page = self.client.get("/barangay/staff/documents/")
            self.assertContains(page, f'action="/barangay/staff/documents/{ticket.pk}/action/"')
            self.assertContains(page, "Start Processing")
            response = self.client.post(
                f"/barangay/staff/documents/{ticket.pk}/action/", {"action": "start"},
            )
        self.assertRedirects(response, "/barangay/staff/documents/", fetch_redirect_response=False)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)
        self.assertEqual(ticket.served_by_id, self.staff.pk)

    def test_slot_end_boundary_expires_and_blocks_direct_document_start(self):
        ticket = self._ticket("boundary-document", "Boundary", self.service, "C12")
        ticket.served_by = None
        ticket.save(update_fields=["served_by", "updated_at"])
        slot_end = timezone.make_aware(datetime.combine(
            ticket.appointment.appointment_date, self.slot.end_time,
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=slot_end):
            response = self.client.post(
                f"/barangay/staff/documents/{ticket.pk}/action/", {"action": "start"},
            )
        self.assertRedirects(response, "/barangay/staff/documents/", fetch_redirect_response=False)
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.status, Appointment.Status.MISSED)
        self.assertEqual(ticket.status, QueueTicket.Status.MISSED)
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.NONE)

    def test_started_processing_is_protected_after_slot_end(self):
        ticket = self._ticket("ongoing-document", "Ongoing", self.service, "C13")
        ticket.appointment.status = Appointment.Status.ONGOING
        ticket.appointment.save(update_fields=["status", "updated_at"])
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        slot_end = timezone.make_aware(datetime.combine(
            ticket.appointment.appointment_date, self.slot.end_time,
        ))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=slot_end):
            self.client.get("/barangay/staff/documents/")
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.status, Appointment.Status.ONGOING)
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)

    def test_staff_cannot_start_document_from_another_barangay(self):
        ticket = self._ticket("foreign-document", "Foreign", self.service, "C14")
        other_barangay = Barangay.objects.create(
            name="Foreign Document Barangay", address="Toledo City", contact_number="09440000000",
        )
        ticket.appointment.barangay = other_barangay
        ticket.appointment.save(update_fields=["barangay", "updated_at"])
        response = self.client.post(
            f"/barangay/staff/documents/{ticket.pk}/action/", {"action": "start"},
        )
        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.NONE)

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

        before_slot_end = timezone.make_aware(datetime.combine(today, time(8, 30)))
        with patch("qq.services.appointment_expiration.timezone.now", return_value=before_slot_end):
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
        self.assertContains(response, "Expired")
        self.assertContains(response, '<span class="done">Expired</span>')

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
        self.assertContains(archived, "Only overdue, unfinished appointments can be archived.")
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)
        self.assertEqual(ticket.status, original_queue_status)
        self.assertEqual(Notification.objects.count(), notification_count)
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
        self.assertContains(documents_page, 'class="workflow-purpose-edit">Edit</button>')
        self.assertContains(documents_page, 'class="workflow-purpose-form"')
        self.assertContains(documents_page, 'name="purpose"')
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

        modal_saved = self.client.post(
            preview_url,
            {"purpose": "Updated directly in processing modal", "sitio": "Purok 9"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(modal_saved.status_code, 200)
        self.assertJSONEqual(modal_saved.content, {
            "ok": True,
            "purpose": "Updated directly in processing modal",
            "display_purpose": "Updated directly in processing modal",
        })
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.purpose, "Updated directly in processing modal")
        self.assertNotEqual(ticket.appointment.sitio, "Purok 9")

        refreshed = self.client.get(preview_url)
        self.assertContains(refreshed, "Updated directly in processing modal")
        downloaded = self.client.get(f"{preview_url}?download=1")
        self.assertEqual(downloaded["Content-Type"], "text/plain")
        self.assertContains(downloaded, "Purpose: Updated directly in processing modal")
        self.assertContains(
            downloaded,
            f"Purok / Sitio: {ticket.appointment.sitio or 'Not provided'}",
        )
        printed = self.client.get(f"{preview_url}?print=1")
        self.assertContains(printed, "Updated directly in processing modal")
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

        ajax_response = self.client.post(
            preview_url,
            {"purpose": "x" * 501},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(ajax_response.status_code, 400)
        self.assertIn("at most 500 characters", ajax_response.json()["error"])
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.purpose, "Original purpose")

    def test_only_assigned_staff_can_edit_and_complete_document(self):
        ticket = self._ticket("assigned-document", "Assigned", self.service, "C18")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        ticket.appointment.purpose = "Original assigned purpose"
        ticket.appointment.save(update_fields=["purpose", "updated_at"])
        preview_url = f"/barangay/staff/documents/{ticket.pk}/preview/"

        staff_b_user = User.objects.create_user(username="workflow-staff-b", password="secret")
        staff_b = BarangayStaff.objects.create(
            barangay=self.barangay,
            user=staff_b_user,
            first_name="Second",
            last_name="Staff",
            username="workflow-staff-b",
            role=BarangayStaff.Role.STAFF,
        )
        self.client.force_login(staff_b_user)

        documents = self.client.get("/barangay/staff/documents/")
        self.assertContains(documents, self.staff.full_name)
        self.assertContains(documents, "This document is assigned to another staff member.")
        self.assertContains(documents, "View Document")
        self.assertNotContains(documents, 'class="workflow-purpose-edit"')
        self.assertNotContains(documents, 'class="done-workflow"')

        read_only_preview = self.client.get(preview_url)
        self.assertEqual(read_only_preview.status_code, 200)
        self.assertContains(read_only_preview, "This document is assigned to another staff member.")
        self.assertContains(read_only_preview, "View Only")
        self.assertNotContains(read_only_preview, 'class="edit-purpose"')
        self.assertNotContains(read_only_preview, 'class="done-action"')

        unauthorized_edit = self.client.post(
            preview_url,
            {"purpose": "Unauthorized edit"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(unauthorized_edit.status_code, 403)
        unauthorized_done = self.client.post(
            preview_url,
            {"action": "complete"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(unauthorized_done.status_code, 403)
        unauthorized_legacy_ready = self.client.post(
            f"/barangay/staff/documents/{ticket.pk}/action/",
            {"action": "ready"},
            follow=True,
        )
        self.assertContains(
            unauthorized_legacy_ready,
            "This document is assigned to another staff member.",
        )
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.PROCESSING)
        self.assertEqual(ticket.appointment.purpose, "Original assigned purpose")
        self.assertEqual(ticket.served_by, self.staff)

        self.client.force_login(self.staff_user)
        assigned_preview = self.client.get(preview_url)
        self.assertContains(assigned_preview, 'class="edit-purpose"')
        self.assertContains(assigned_preview, 'class="done-action"')
        assigned_edit = self.client.post(
            preview_url,
            {"purpose": "Updated by assigned staff"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(assigned_edit.status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            assigned_done = self.client.post(
                preview_url,
                {"action": "complete"},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
        self.assertEqual(assigned_done.status_code, 200)
        ticket.refresh_from_db()
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.READY)
        self.assertEqual(ticket.appointment.purpose, "Updated by assigned staff")
        self.assertEqual(ticket.served_by, self.staff)
        self.assertEqual(
            Notification.objects.filter(
                appointment=ticket.appointment,
                title="Document Ready for Pickup",
            ).count(),
            1,
        )

        self.client.force_login(staff_b_user)
        claimed = self.client.post(
            f"/barangay/staff/dashboard/documents/{ticket.pk}/claim/",
            follow=True,
        )
        self.assertEqual(claimed.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.claim_status, QueueTicket.ClaimStatus.CLAIMED)
        self.assertEqual(ticket.served_by, self.staff)
        completed = self.client.get("/barangay/staff/documents/?tab=completed")
        completed_table = completed.content.decode().split(
            '<section class="archive-table">', 1
        )[1].split("</section>", 1)[0]
        self.assertIn(self.staff.full_name, completed_table)
        self.assertNotIn(staff_b.full_name, completed_table)

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

    def test_document_completion_uses_explicit_numeric_id_and_url_not_form_action_property(self):
        ticket = self._ticket("completion-url", "Completion URL", self.service, "C19")
        ticket.claim_status = QueueTicket.ClaimStatus.PROCESSING
        ticket.save(update_fields=["claim_status", "updated_at"])
        completion_url = f"/barangay/staff/documents/{ticket.pk}/preview/"

        response = self.client.get("/barangay/staff/documents/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-document-id="{ticket.pk}"')
        self.assertContains(response, f'data-completion-url="{completion_url}"')
        completion_script = response.content.decode().split(
            "document.querySelectorAll('.complete-document-form')", 1
        )[1].split("document.querySelectorAll('.workflow-purpose')", 1)[0]
        self.assertIn("fetch(requestUrl", completion_script)
        self.assertNotIn("fetch(form.action", completion_script)

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

        original_purpose = ticket.appointment.purpose
        purpose_response = self.client.post(
            f"/barangay/staff/documents/{ticket.pk}/preview/",
            {"purpose": "Unauthorized purpose change"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(purpose_response.status_code, 404)
        ticket.appointment.refresh_from_db()
        self.assertEqual(ticket.appointment.purpose, original_purpose)
