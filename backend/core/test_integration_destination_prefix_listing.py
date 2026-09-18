from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationPrefixListingTests(TestCase):
    def test_listing_exposes_prefix_but_not_digest(self):
        organization = Organization.objects.create(name="Prefix Listing Tenant")
        owner = User.objects.create_user(username="prefix-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        item = client.get("/api/integrations/destinations/").data[0]
        self.assertIn("signing_secret_prefix", item)
        self.assertNotIn("signing_secret_digest", item)
