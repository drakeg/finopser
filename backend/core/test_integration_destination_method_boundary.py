from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationMethodBoundaryTests(TestCase):
    def test_destination_detail_does_not_support_mutating_put_or_delete(self):
        organization = Organization.objects.create(name="Method Boundary Tenant")
        owner = User.objects.create_user(username="method-owner", password="test-password-long")
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
        self.assertEqual(client.put(f"/api/integrations/destinations/{destination_id}/", {}, format="json").status_code, 405)
        self.assertEqual(client.delete(f"/api/integrations/destinations/{destination_id}/").status_code, 405)
