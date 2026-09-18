from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination, NotificationChannel
from .models import Organization


class NotificationChannelLifecycleTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Channel Tenant")
        self.manager = User.objects.create_user(username="channel-manager", password="test-password-long")
        OrganizationMembership.objects.create(user=self.manager, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        self.destination = IntegrationDestination.objects.create(
            organization=self.organization,
            name="alerts-hook",
            endpoint_url="http://localhost:9999/alerts",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="finopser_whsec_a",
            created_by=self.manager,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_manager_creates_lists_and_disables_channel(self):
        response = self.client.post("/api/notification-channels/", {"name": "governance-alerts", "destination": self.destination.id, "event_types": ["governance.finding", "report.ready"]}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("signing_secret", response.data)
        channel_id = response.data["id"]
        self.assertEqual(self.client.get("/api/notification-channels/").status_code, 200)
        disabled = self.client.post(f"/api/notification-channels/{channel_id}/disable/", {}, format="json")
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.data["is_active"])

    def test_unknown_event_and_inactive_destination_fail_closed(self):
        response = self.client.post("/api/notification-channels/", {"name": "bad", "destination": self.destination.id, "event_types": ["unknown.event"]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.destination.is_active = False
        self.destination.save(update_fields=["is_active"])
        response = self.client.post("/api/notification-channels/", {"name": "inactive", "destination": self.destination.id, "event_types": ["cost.threshold"]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cross_tenant_destination_and_channel_are_hidden(self):
        other = Organization.objects.create(name="Other Tenant")
        outsider = User.objects.create_user(username="other-channel-manager", password="test-password-long")
        OrganizationMembership.objects.create(user=outsider, organization=other, role=OrganizationMembership.Role.OWNER)
        channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="private", event_types=["report.ready"], created_by=self.manager)
        self.client.force_authenticate(outsider)
        create = self.client.post("/api/notification-channels/", {"name": "cross", "destination": self.destination.id, "event_types": ["report.ready"]}, format="json")
        self.assertEqual(create.status_code, 400)
        self.assertEqual(self.client.get(f"/api/notification-channels/{channel.id}/").status_code, 404)

    def test_non_manager_cannot_manage_channels(self):
        viewer = User.objects.create_user(username="channel-viewer", password="test-password-long")
        OrganizationMembership.objects.create(user=viewer, organization=self.organization, role=OrganizationMembership.Role.VIEWER)
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get("/api/notification-channels/").status_code, 403)
