from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationPrefixMatchTests(TestCase):
    def test_returned_prefix_matches_generated_secret(self):
        organization = Organization.objects.create(name="Prefix Match Tenant")
        owner = User.objects.create_user(username="prefix-match-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertTrue(response.data["signing_secret"].startswith(response.data["signing_secret_prefix"]))
