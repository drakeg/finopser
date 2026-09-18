from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationOrderingTests(TestCase):
    def test_listing_is_ordered_by_name(self):
        organization = Organization.objects.create(name="Ordering Tenant")
        owner = User.objects.create_user(username="ordering-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        for name in ["zeta", "alpha"]:
            IntegrationDestination.objects.create(
                organization=organization,
                name=name,
                endpoint_url="https://example.test/events",
                signing_secret_digest=name[0] * 64,
                signing_secret_prefix=f"prefix-{name}",
                created_by=owner,
            )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/integrations/destinations/")
        self.assertEqual([item["name"] for item in response.data], ["alpha", "zeta"])
