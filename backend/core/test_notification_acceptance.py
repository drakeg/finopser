from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDelivery, IntegrationDestination, NotificationChannel
from .models import Organization


class NotificationAcceptanceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Notification Acceptance")
        self.manager = User.objects.create_user(username="notification-acceptance-manager", password="test-password-long")
        OrganizationMembership.objects.create(user=self.manager, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        self.destination = IntegrationDestination.objects.create(organization=self.organization, name="acceptance-hook", endpoint_url="http://localhost:9999/hook", signing_secret_digest="a" * 64, signing_secret_prefix="finopser_whsec_a", created_by=self.manager)
        self.channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="acceptance-channel", event_types=["cost.threshold"], created_by=self.manager)\n        self.other_channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="shared-destination-channel", event_types=["cost.threshold"], created_by=self.manager)
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_local_dispatch_history_deduplication_and_disabled_state(self):
        url = f"/api/notification-channels/{self.channel.id}/test/"
        first = self.client.post(url, {"event_type": "cost.threshold", "source_id": "budget-42"}, format="json")
        second = self.client.post(url, {"event_type": "cost.threshold", "source_id": "budget-42"}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(IntegrationDelivery.objects.count(), 1)\n        self.assertEqual(IntegrationDelivery.objects.get().channel_id, self.channel.id)
        history = self.client.get(f"/api/notification-channels/{self.channel.id}/deliveries/")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data[0]["id"], first.data["id"])
        self.assertNotIn("signing_secret", history.data[0])\n        other_history = self.client.get(f"/api/notification-channels/{self.other_channel.id}/deliveries/")\n        self.assertEqual(other_history.status_code, 200)\n        self.assertEqual(other_history.data, [])
        self.client.post(f"/api/notification-channels/{self.channel.id}/disable/", {}, format="json")
        self.assertEqual(self.client.post(url, {"event_type": "cost.threshold", "source_id": "budget-43"}, format="json").status_code, 409)

    def test_unsubscribed_cross_tenant_and_non_manager_fail_closed(self):
        self.assertEqual(self.client.post(f"/api/notification-channels/{self.channel.id}/test/", {"event_type": "report.ready"}, format="json").status_code, 400)
        other = Organization.objects.create(name="Other Notification Tenant")
        outsider = User.objects.create_user(username="notification-outsider", password="test-password-long")
        OrganizationMembership.objects.create(user=outsider, organization=other, role=OrganizationMembership.Role.OWNER)
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(f"/api/notification-channels/{self.channel.id}/deliveries/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/notification-channels/{self.channel.id}/test/", {"event_type": "cost.threshold"}, format="json").status_code, 404)
        viewer = User.objects.create_user(username="notification-viewer", password="test-password-long")
        OrganizationMembership.objects.create(user=viewer, organization=self.organization, role=OrganizationMembership.Role.VIEWER)
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get(f"/api/notification-channels/{self.channel.id}/deliveries/").status_code, 403)
