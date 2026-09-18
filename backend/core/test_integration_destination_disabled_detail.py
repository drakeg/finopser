from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationDisabledHistoryTests(TestCase):
    def test_disabled_destination_remains_inspectable(self):
        organization = Organization.objects.create(name="Disabled History Tenant")
        owner = User.objects.create_user(username="disabled-history-owner", password="test-password-long")
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
        client.post(f"/api/integrations/destinations/{destination_id}/disable/")
        detail = client.get(f"/api/integrations/destinations/{destination_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.data["is_active"])
        self.assertIsNotNone(detail.data["disabled_at"])
