from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationStateSecretTests(TestCase):
    def test_disable_and_enable_do_not_return_secret(self):
        organization = Organization.objects.create(name="State Secret Tenant")
        owner = User.objects.create_user(username="state-secret-owner", password="test-password-long")
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
        secret = created.data["signing_secret"]
        disabled = client.post(f"/api/integrations/destinations/{destination_id}/disable/")
        enabled = client.post(f"/api/integrations/destinations/{destination_id}/enable/")
        self.assertNotIn(secret, str(disabled.data))
        self.assertNotIn(secret, str(enabled.data))
        self.assertNotIn("signing_secret", disabled.data)
        self.assertNotIn("signing_secret", enabled.data)
