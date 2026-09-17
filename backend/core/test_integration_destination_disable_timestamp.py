from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationDisableTimestampTests(TestCase):
    def test_disable_sets_timestamp_and_enable_clears_it(self):
        organization = Organization.objects.create(name="Timestamp Tenant")
        owner = User.objects.create_user(username="timestamp-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        created = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        destination_id = created.data["id"]
        disabled = client.post(f"/api/integrations/destinations/{destination_id}/disable/")
        self.assertIsNotNone(disabled.data["disabled_at"])
        enabled = client.post(f"/api/integrations/destinations/{destination_id}/enable/")
        self.assertIsNone(enabled.data["disabled_at"])
