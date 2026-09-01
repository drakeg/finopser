from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .account_models import Notification, NotificationReceipt, OrganizationMembership
from .models import Organization
from .notifications import external_delivery_configured, notify


@override_settings(NOTIFICATION_PROVIDER="disabled")
class NotificationFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notify-user", password="test-password-long")
        self.teammate = User.objects.create_user(
            username="notify-teammate",
            password="test-password-long",
        )
        self.organization = Organization.objects.create(name="Notification Workspace")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            user=self.teammate,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        self.other = Organization.objects.create(name="Other Notification Workspace")
        self.client = APIClient()
        self.client.login(username="notify-user", password="test-password-long")

    def test_disabled_external_delivery_is_default_safe(self):
        self.assertFalse(external_delivery_configured())

    def test_notify_deduplicates_and_reopens_existing_notification_for_everyone(self):
        notification, created = notify(
            self.organization,
            dedupe_key="budget:42:2026-09:critical",
            category="budget",
            severity=Notification.Severity.HIGH,
            title="Budget threshold reached",
            target="Budgets",
            object_type="Budget",
            object_id="42",
        )
        self.assertTrue(created)
        NotificationReceipt.objects.create(notification=notification, user=self.user, read_at=notification.first_seen)
        NotificationReceipt.objects.create(
            notification=notification,
            user=self.teammate,
            read_at=notification.first_seen,
        )

        repeated, created = notify(
            self.organization,
            dedupe_key="budget:42:2026-09:critical",
            category="budget",
            severity=Notification.Severity.CRITICAL,
            title="Budget exceeded",
            target="Budgets",
            object_type="Budget",
            object_id="42",
        )

        self.assertFalse(created)
        self.assertEqual(repeated.id, notification.id)
        self.assertEqual(repeated.occurrence_count, 2)
        self.assertFalse(NotificationReceipt.objects.filter(notification=repeated).exists())
        self.assertEqual(Notification.objects.filter(organization=self.organization).count(), 1)

    def test_list_and_unread_count_are_tenant_scoped(self):
        notify(
            self.organization,
            dedupe_key="mine",
            category="policy",
            severity=Notification.Severity.HIGH,
            title="My policy alert",
        )
        notify(
            self.other,
            dedupe_key="theirs",
            category="policy",
            severity=Notification.Severity.CRITICAL,
            title="Other tenant alert",
        )

        listing = self.client.get("/api/notifications/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()["results"]), 1)
        self.assertEqual(listing.json()["results"][0]["title"], "My policy alert")
        self.assertFalse(listing.json()["results"][0]["is_read"])

        count = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(count.status_code, 200)
        self.assertEqual(count.json()["unread"], 1)

    def test_read_state_is_per_user_within_same_workspace(self):
        notification, _ = notify(
            self.organization,
            dedupe_key="shared-read-state",
            category="policy",
            severity=Notification.Severity.HIGH,
            title="Shared workspace alert",
        )

        response = self.client.post(
            f"/api/notifications/{notification.id}/read/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_read"])
        self.assertEqual(self.client.get("/api/notifications/unread-count/").json()["unread"], 0)

        teammate_client = APIClient()
        teammate_client.login(username="notify-teammate", password="test-password-long")
        teammate_listing = teammate_client.get("/api/notifications/")
        self.assertEqual(teammate_listing.status_code, 200)
        self.assertFalse(teammate_listing.json()["results"][0]["is_read"])
        self.assertEqual(teammate_client.get("/api/notifications/unread-count/").json()["unread"], 1)

    def test_read_state_actions_cannot_cross_tenant_boundary(self):
        mine, _ = notify(
            self.organization,
            dedupe_key="mine-read",
            category="sync",
            severity=Notification.Severity.WARNING,
            title="Sync failed",
        )
        theirs, _ = notify(
            self.other,
            dedupe_key="theirs-read",
            category="sync",
            severity=Notification.Severity.WARNING,
            title="Other sync failed",
        )

        response = self.client.post(f"/api/notifications/{mine.id}/read/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_read"])
        self.assertIsNotNone(response.json()["read_at"])
        self.assertTrue(NotificationReceipt.objects.filter(notification=mine, user=self.user).exists())

        blocked = self.client.post(f"/api/notifications/{theirs.id}/read/", {}, format="json")
        self.assertEqual(blocked.status_code, 404)
        self.assertFalse(NotificationReceipt.objects.filter(notification=theirs, user=self.user).exists())

        unread = self.client.post(f"/api/notifications/{mine.id}/unread/", {}, format="json")
        self.assertEqual(unread.status_code, 200)
        self.assertFalse(unread.json()["is_read"])
        self.assertIsNone(unread.json()["read_at"])
        self.assertFalse(NotificationReceipt.objects.filter(notification=mine, user=self.user).exists())

    def test_mark_all_read_only_updates_current_workspace_and_current_user(self):
        mine, _ = notify(
            self.organization,
            dedupe_key="all-mine",
            category="recommendation",
            severity=Notification.Severity.INFO,
            title="Recommendation ready",
        )
        theirs, _ = notify(
            self.other,
            dedupe_key="all-theirs",
            category="recommendation",
            severity=Notification.Severity.INFO,
            title="Other recommendation ready",
        )

        response = self.client.post("/api/notifications/mark-all-read/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)
        self.assertTrue(NotificationReceipt.objects.filter(notification=mine, user=self.user).exists())
        self.assertFalse(NotificationReceipt.objects.filter(notification=mine, user=self.teammate).exists())
        self.assertFalse(NotificationReceipt.objects.filter(notification=theirs, user=self.user).exists())

    def test_superuser_scope_is_explicitly_global_but_receipts_remain_personal(self):
        first, _ = notify(
            self.organization,
            dedupe_key="super-one",
            category="billing",
            severity=Notification.Severity.WARNING,
            title="First billing alert",
        )
        notify(
            self.other,
            dedupe_key="super-two",
            category="billing",
            severity=Notification.Severity.WARNING,
            title="Second billing alert",
        )
        admin = User.objects.create_superuser(
            username="notify-superuser",
            password="test-password-long",
            email="admin@example.test",
        )
        self.client.logout()
        self.client.login(username=admin.username, password="test-password-long")

        listing = self.client.get("/api/notifications/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()["results"]), 2)
        self.client.post(f"/api/notifications/{first.id}/read/", {}, format="json")
        self.assertTrue(NotificationReceipt.objects.filter(notification=first, user=admin).exists())
        self.assertFalse(NotificationReceipt.objects.filter(notification=first, user=self.user).exists())
