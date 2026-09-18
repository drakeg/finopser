from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationUnknownTests(TestCase):
    def test_unknown_destination_returns_404(self):
        organization = Organization.objects.create(name="Unknown Destination Tenant")
        owner = User.objects.create_user(username="unknown-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        self.assertEqual(client.get("/api/integrations/destinations/999999/").status_code, 404)
        self.assertEqual(client.post("/api/integrations/destinations/999999/enable/").status_code, 404)
