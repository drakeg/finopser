from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationDisabledListingTests(TestCase):
    def test_disabled_destination_remains_in_listing(self):
        organization = Organization.objects.create(name="Disabled Listing Tenant")
        owner = User.objects.create_user(username="disabled-listing-owner", password="test-password-long")
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
        client.post(f"/api/integrations/destinations/{created.data['id']}/disable/")
        listed = client.get("/api/integrations/destinations/")
        self.assertEqual(len(listed.data), 1)
        self.assertFalse(listed.data[0]["is_active"])
