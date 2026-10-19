from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from qq.models import Appointment, Barangay, BarangayAdminRegistration, BarangayStaff, Resident, Service


class SuperAdminAuthenticationTests(TestCase):
    password = "StrongPass1!"

    def setUp(self):
        self.barangay = Barangay.objects.create(
            name="Authentication Test Barangay",
            address="Toledo City",
            contact_number="09123456789",
        )

    def _create_staff(self, username, role):
        user = User.objects.create_user(username=username, password=self.password, is_staff=True)
        BarangayStaff.objects.create(
            user=user,
            barangay=self.barangay,
            first_name="Test",
            last_name="User",
            username=username,
            role=role,
        )
        return user

    def test_shared_signin_password_control_starts_hidden_and_accessible(self):
        response = self.client.get(reverse("signin"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="password" name="password" type="password"')
        self.assertContains(response, 'class="password-toggle" type="button" aria-label="Show password" aria-pressed="false"')
        self.assertContains(response, 'class="eye-off"')
        self.assertContains(response, 'class="eye"')

    def test_superuser_login_redirects_to_superadmin_dashboard_first(self):
        superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password=self.password,
        )
        # A linked barangay profile must not take precedence over superuser access.
        self.barangay.user = superuser
        self.barangay.save(update_fields=["user"])

        response = self.client.post(reverse("signin"), {
            "username": superuser.username,
            "password": self.password,
        })

        self.assertRedirects(response, reverse("superadmin_dashboard"), fetch_redirect_response=False)

    def test_barangay_admin_login_keeps_existing_redirect(self):
        admin_user = self._create_staff("barangay-admin", BarangayStaff.Role.ADMIN)

        response = self.client.post(reverse("signin"), {
            "username": admin_user.username,
            "password": self.password,
        })

        self.assertRedirects(response, reverse("barangay_dashboard"), fetch_redirect_response=False)

    def test_barangay_staff_login_keeps_existing_redirect(self):
        staff_user = self._create_staff("barangay-staff", BarangayStaff.Role.STAFF)

        response = self.client.post(reverse("signin"), {
            "username": staff_user.username,
            "password": self.password,
        })

        self.assertRedirects(response, reverse("staff_dashboard"), fetch_redirect_response=False)

    def test_resident_web_signin_behavior_is_unchanged(self):
        resident_user = User.objects.create_user(username="resident", password=self.password)
        Resident.objects.create(
            user=resident_user,
            first_name="Test",
            last_name="Resident",
            birthdate="2000-01-01",
            sex=Resident.Sex.MALE,
            contact_number="09999999999",
            barangay=self.barangay,
        )

        response = self.client.post(reverse("signin"), {
            "username": resident_user.username,
            "password": self.password,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resident access is available in the QuickQueue mobile app.")
        self.assertEqual(int(self.client.session["_auth_user_id"]), resident_user.pk)

    def test_anonymous_user_is_redirected_to_signin(self):
        response = self.client.get(reverse("superadmin_dashboard"))

        self.assertRedirects(
            response,
            f'{reverse("signin")}?next={reverse("superadmin_dashboard")}',
            fetch_redirect_response=False,
        )

    def test_authenticated_non_superuser_is_forbidden(self):
        user = User.objects.create_user(username="ordinary-user", password=self.password)
        self.client.force_login(user)

        response = self.client.get(reverse("superadmin_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_portal_and_django_admin(self):
        superuser = User.objects.create_superuser(
            username="admin-access",
            email="admin-access@example.com",
            password=self.password,
        )
        self.client.force_login(superuser)

        dashboard_response = self.client.get(reverse("superadmin_dashboard"))
        django_admin_response = self.client.get(reverse("admin:index"))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "QuickQueue System Administrator Dashboard")
        self.assertEqual(django_admin_response.status_code, 200)

    def test_logout_ends_superuser_session(self):
        superuser = User.objects.create_superuser(
            username="logout-admin",
            email="logout-admin@example.com",
            password=self.password,
        )
        self.client.force_login(superuser)

        response = self.client.get(reverse("staff_logout"))

        self.assertRedirects(response, reverse("signin"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_all_superadmin_navigation_pages_are_shared_and_protected(self):
        route_names = (
            "superadmin_dashboard",
            "superadmin_barangays",
            "superadmin_barangay_admins",
            "superadmin_system_settings",
        )
        superuser = User.objects.create_superuser(
            username="navigation-admin",
            email="navigation-admin@example.com",
            password=self.password,
        )
        self.client.force_login(superuser)

        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "superadmin/base.html")
                self.assertTemplateUsed(response, "superadmin/components/sidebar.html")
                self.assertContains(response, f'class="active" href="{reverse(route_name)}"')
                self.assertContains(response, "qq/images/qqlogo.png")
                self.assertContains(response, "System Administrator Portal")

        self.client.logout()
        non_superuser = User.objects.create_user(
            username="blocked-navigation-user",
            password=self.password,
        )
        self.client.force_login(non_superuser)
        for route_name in route_names:
            with self.subTest(blocked_route_name=route_name):
                self.assertEqual(self.client.get(reverse(route_name)).status_code, 403)


class SuperAdminDashboardDataTests(TestCase):
    password = "StrongPass1!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="dashboard-superuser",
            email="dashboard@example.com",
            password=self.password,
        )
        self.client.force_login(self.superuser)
        self.today = timezone.localdate()
        self.initial_barangays = Barangay.objects.count()
        self.initial_residents = Resident.objects.count()
        self.initial_today_appointments = Appointment.objects.filter(appointment_date=self.today).count()
        self.barangay_one = Barangay.objects.create(
            name="Barangay One",
            address="Toledo City",
            contact_number="09111111111",
        )
        self.barangay_two = Barangay.objects.create(
            name="Barangay Two",
            address="Toledo City",
            contact_number="09222222222",
        )
        self.service = Service.objects.create(
            code="DASH",
            name="Dashboard Test Service",
            description="Dashboard data verification",
            estimated_duration=15,
        )

    def _resident(self, username, barangay, contact):
        user = User.objects.create_user(username=username, password=self.password)
        return Resident.objects.create(
            user=user,
            first_name="Dashboard",
            last_name=username,
            birthdate="2000-01-01",
            sex=Resident.Sex.MALE,
            contact_number=contact,
            barangay=barangay,
        )

    def _registration(self, username, barangay, status):
        user = User.objects.create_user(username=username, password=self.password)
        return BarangayAdminRegistration.objects.create(
            user=user,
            barangay=barangay,
            municipality="Toledo City",
            province="Cebu",
            complete_address="Test address",
            zip_code="6038",
            contact_number=f"093{user.pk:08d}"[-11:],
            email=f"{username}@example.com",
            status=status,
            reviewed_at=timezone.now() if status != BarangayAdminRegistration.Status.PENDING else None,
        )

    def test_dashboard_statistics_ignore_historical_verification_records(self):
        direct_admin = User.objects.create_user(username="direct-admin", password=self.password, is_staff=True)
        self.barangay_one.user = direct_admin
        self.barangay_one.save(update_fields=["user"])
        # The same account represented in both supported admin relationships counts once.
        BarangayStaff.objects.create(
            user=direct_admin,
            barangay=self.barangay_one,
            first_name="Direct",
            last_name="Admin",
            username=direct_admin.username,
            role=BarangayStaff.Role.ADMIN,
        )
        second_admin = User.objects.create_user(username="staff-admin", password=self.password, is_staff=True)
        BarangayStaff.objects.create(
            user=second_admin,
            barangay=self.barangay_two,
            first_name="Staff",
            last_name="Admin",
            username=second_admin.username,
            role=BarangayStaff.Role.ADMIN,
        )
        resident_one = self._resident("resident-one", self.barangay_one, "09411111111")
        resident_two = self._resident("resident-two", self.barangay_two, "09422222222")
        Appointment.objects.create(
            resident=resident_one, barangay=self.barangay_one, service=self.service,
            appointment_date=self.today, queue_number="A-1",
        )
        Appointment.objects.create(
            resident=resident_two, barangay=self.barangay_two, service=self.service,
            appointment_date=self.today, queue_number="A-2",
        )
        self._registration("pending-admin", self.barangay_one, BarangayAdminRegistration.Status.PENDING)
        self._registration("approved-admin", self.barangay_one, BarangayAdminRegistration.Status.APPROVED)
        self._registration("rejected-admin", self.barangay_two, BarangayAdminRegistration.Status.REJECTED)
        self._registration("approved-admin-two", self.barangay_two, BarangayAdminRegistration.Status.APPROVED)

        response = self.client.get(reverse("superadmin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_barangays"], self.initial_barangays + 2)
        self.assertEqual(response.context["total_admins"], 2)
        self.assertEqual(response.context["total_residents"], self.initial_residents + 2)
        self.assertEqual(response.context["today_appointments"], self.initial_today_appointments + 2)
        self.assertNotIn("total_applications", response.context)
        self.assertNotContains(response, "Verification Report")
        self.assertNotContains(response, "Pending Verifications")
        self.assertEqual(BarangayAdminRegistration.objects.count(), 4)

    def test_appointment_chart_groups_barangays_and_filters_dates(self):
        resident_one = self._resident("chart-one", self.barangay_one, "09511111111")
        resident_two = self._resident("chart-two", self.barangay_two, "09522222222")
        for index in range(2):
            Appointment.objects.create(
                resident=resident_one, barangay=self.barangay_one, service=self.service,
                appointment_date=self.today, queue_number=f"B-{index}",
            )
        Appointment.objects.create(
            resident=resident_two, barangay=self.barangay_two, service=self.service,
            appointment_date=self.today - timedelta(days=10), queue_number="OLD-1",
        )

        today_response = self.client.get(reverse("superadmin_dashboard"), {"period": "today"})
        last_seven_response = self.client.get(reverse("superadmin_dashboard"), {"period": "last_7_days"})
        year_response = self.client.get(reverse("superadmin_dashboard"), {"period": "this_year"})

        self.assertEqual(today_response.context["appointment_counts"], [
            {"barangay__name": "Barangay One", "total": 2, "percentage": 100}
        ])
        self.assertEqual(last_seven_response.context["appointment_counts"], [
            {"barangay__name": "Barangay One", "total": 2, "percentage": 100}
        ])
        year_counts = {item["barangay__name"]: item["total"] for item in year_response.context["appointment_counts"]}
        self.assertEqual(year_counts, {"Barangay One": 2, "Barangay Two": 1})

    def test_dashboard_displays_empty_states_without_records(self):
        Barangay.objects.all().delete()

        response = self.client.get(reverse("superadmin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No appointment records")
        self.assertContains(response, "No recorded activities")


class SuperAdminBarangayManagementTests(TestCase):
    password = "StrongPass1!"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="barangay-manager",
            email="manager@example.com",
            password=self.password,
        )
        self.client.force_login(self.superuser)
        self.barangay = Barangay.objects.create(
            name="Management Test Barangay",
            address="Old Address, Toledo City",
            contact_number="09123450000",
            email="old@example.com",
        )

    def test_superuser_can_view_barangay_management_and_details(self):
        administrator = User.objects.create_user(
            username="assigned-administrator",
            first_name="Assigned",
            last_name="Administrator",
            password=self.password,
        )
        self.barangay.user = administrator
        self.barangay.save(update_fields=["user"])

        list_response = self.client.get(reverse("superadmin_barangays"))
        detail_response = self.client.get(reverse("superadmin_barangay_detail", args=[self.barangay.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.barangay.name)
        self.assertContains(list_response, "Assigned Administrator")
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, self.barangay.address)
        self.assertContains(detail_response, "Assigned Administrator")

    def test_barangay_details_panel_is_hidden_by_default_and_opens_for_selection(self):
        default_response = self.client.get(reverse("superadmin_barangays"))

        self.assertIsNone(default_response.context["selected_barangay"])
        self.assertContains(
            default_response,
            'id="barangay-selection" aria-label="Selected barangay details" hidden',
        )
        self.assertNotContains(default_response, 'id="barangay-management" class="panel-open"')

        selected_response = self.client.get(
            reverse("superadmin_barangays"), {"selected": self.barangay.pk}
        )

        self.assertEqual(selected_response.context["selected_barangay"], self.barangay)
        self.assertContains(selected_response, "split-management panel-open")
        self.assertContains(selected_response, "Close selected barangay details")

    def test_superuser_can_create_barangay_and_dashboard_total_updates(self):
        before = self.client.get(reverse("superadmin_dashboard")).context["total_barangays"]

        response = self.client.post(reverse("superadmin_barangay_add"), {
            "name": "New Barangay",
            "address": "New Address, Toledo City",
            "contact_number": "09999999999",
            "email": "new@example.com",
            "is_active": "on",
        })

        self.assertRedirects(response, reverse("superadmin_barangays"))
        created = Barangay.objects.get(name="New Barangay")
        self.assertIsNone(created.user_id)
        self.assertTrue(created.is_active)
        after = self.client.get(reverse("superadmin_dashboard")).context["total_barangays"]
        self.assertEqual(after, before + 1)

    def test_duplicate_barangay_name_is_rejected_case_insensitively(self):
        response = self.client.post(reverse("superadmin_barangay_add"), {
            "name": "  management test barangay  ",
            "address": "Duplicate Address",
            "contact_number": "09888888888",
            "email": "duplicate@example.com",
            "is_active": "on",
        })

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "A barangay with this name already exists.", status_code=400)
        self.assertEqual(Barangay.objects.filter(name__iexact="Management Test Barangay").count(), 1)

    def test_superuser_can_edit_without_changing_relationships(self):
        administrator = User.objects.create_user(username="preserved-admin", password=self.password)
        self.barangay.user = administrator
        self.barangay.save(update_fields=["user"])

        response = self.client.post(reverse("superadmin_barangay_edit", args=[self.barangay.pk]), {
            "name": "Updated Barangay",
            "address": "Updated Address, Toledo City",
            "contact_number": "09777777777",
            "email": "updated@example.com",
            "is_active": "on",
        })

        self.assertRedirects(
            response,
            f"{reverse('superadmin_barangays')}?selected={self.barangay.pk}",
        )
        self.barangay.refresh_from_db()
        self.assertEqual(self.barangay.name, "Updated Barangay")
        self.assertEqual(self.barangay.address, "Updated Address, Toledo City")
        self.assertEqual(self.barangay.user, administrator)

    def test_barangay_edit_preserves_safe_management_return_location(self):
        return_to = (
            f"{reverse('superadmin_barangays')}?q=Management&status=active"
            f"&sort=desc&page=1&selected={self.barangay.pk}"
        )
        response = self.client.get(
            reverse("superadmin_barangay_edit", args=[self.barangay.pk]),
            {"return_to": return_to},
        )

        self.assertNotContains(response, "Back to Barangays")
        self.assertContains(response, 'aria-label="Close"')
        self.assertContains(response, ">Cancel</button>")
        self.assertContains(response, "You have unsaved changes")
        self.assertContains(response, 'id="barangay-modal" class="barangay-modal" open')
        self.assertContains(response, "removeAttribute('open');modal.showModal()")
        self.assertContains(response, "modal.addEventListener('cancel'")
        self.assertContains(response, "split-management")
        self.assertEqual(response.context["return_url"], return_to)

    def test_search_status_sorting_and_pagination(self):
        self.barangay.is_active = False
        self.barangay.save(update_fields=["is_active"])
        for index in range(11):
            Barangay.objects.create(
                name=f"ZZ Test Barangay {index:02d}",
                address=f"Zone {index}",
                contact_number=f"096{index:08d}"[-11:],
                is_active=True,
            )

        filtered = self.client.get(reverse("superadmin_barangays"), {
            "q": "ZZ Test",
            "status": "active",
            "sort": "desc",
        })
        second_page = self.client.get(reverse("superadmin_barangays"), {
            "q": "ZZ Test",
            "status": "active",
            "page": 2,
        })

        names = [item.name for item in filtered.context["barangay_page"]]
        self.assertEqual(names, sorted(names, reverse=True))
        self.assertNotContains(filtered, self.barangay.name)
        self.assertEqual(filtered.context["barangay_page"].paginator.count, 11)
        self.assertEqual(second_page.context["barangay_page"].number, 2)
        self.assertEqual(len(second_page.context["barangay_page"]), 1)

    def test_status_change_preserves_related_records(self):
        resident_user = User.objects.create_user(username="status-resident", password=self.password)
        resident = Resident.objects.create(
            user=resident_user,
            first_name="Status",
            last_name="Resident",
            birthdate="2000-01-01",
            sex=Resident.Sex.FEMALE,
            contact_number="09555555555",
            barangay=self.barangay,
        )

        response = self.client.post(
            reverse("superadmin_barangay_status", args=[self.barangay.pk]),
            {"status": "inactive"},
        )

        self.assertRedirects(response, reverse("superadmin_barangay_detail", args=[self.barangay.pk]))
        self.barangay.refresh_from_db()
        resident.refresh_from_db()
        self.assertFalse(self.barangay.is_active)
        self.assertEqual(resident.barangay, self.barangay)

    def test_non_superuser_cannot_access_or_modify_barangays(self):
        non_superuser = User.objects.create_user(username="blocked-manager", password=self.password)
        self.client.force_login(non_superuser)
        requests = (
            ("get", reverse("superadmin_barangays"), None),
            ("get", reverse("superadmin_barangay_detail", args=[self.barangay.pk]), None),
            ("get", reverse("superadmin_barangay_edit", args=[self.barangay.pk]), None),
            ("post", reverse("superadmin_barangay_add"), {}),
            ("post", reverse("superadmin_barangay_edit", args=[self.barangay.pk]), {}),
            ("post", reverse("superadmin_barangay_status", args=[self.barangay.pk]), {"status": "inactive"}),
        )
        for method, url, data in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data or {})
                self.assertEqual(response.status_code, 403)
