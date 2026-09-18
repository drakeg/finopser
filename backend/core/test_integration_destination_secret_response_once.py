from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationCopyOnceResponseTests(TestCase):
    def test_secret_appears_only_in_create_response(self):
        organization = Organization.objects.create(name="Copy Once Response Tenant")
        owner = User.objects.create_user(username="copy-once-response-owner", password="test-password-long")
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
        self.assertIn("signing_secret", created.data)
        destination_id = created.data["id"]
        self.assertNotIn("signing_secret", client.get(f"/api/integrations/destinations/{destination_id}/").data)
        self.assertNotIn("signing_secret", client.get("/api/integrations/destinations/").data[0])
        self.assertNotIn("signing_secret", client.post(f"/api/integrations/destinations/{destination_id}/disable/").data)
