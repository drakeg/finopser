from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationListScopeTests(TestCase):
    def test_listing_contains_only_current_tenant(self):
        organizations = [Organization.objects.create(name=f"List Tenant {index}") for index in range(2)]
        owners = []
        for index, organization in enumerate(organizations):
            owner = User.objects.create_user(username=f"list-owner-{index}", password="test-password-long")
            owners.append(owner)
            OrganizationMembership.objects.create(
                user=owner,
                organization=organization,
                role=OrganizationMembership.Role.OWNER,
            )
            IntegrationDestination.objects.create(
                organization=organization,
                name=f"events-{index}",
                endpoint_url="https://example.test/events",
                signing_secret_digest=str(index) * 64,
                signing_secret_prefix=f"prefix-{index}",
                created_by=owner,
            )
        client = APIClient()
        client.force_authenticate(owners[0])
        response = client.get("/api/integrations/destinations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["events-0"])
