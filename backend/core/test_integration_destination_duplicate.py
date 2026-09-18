from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationDuplicateTests(TestCase):
    def test_duplicate_name_returns_conflict(self):
        organization = Organization.objects.create(name="Duplicate Tenant")
        owner = User.objects.create_user(username="duplicate-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        payload = {"name": "events", "endpoint_url": "https://example.test/events"}
        self.assertEqual(client.post("/api/integrations/destinations/", payload, format="json").status_code, 201)
        self.assertEqual(client.post("/api/integrations/destinations/", payload, format="json").status_code, 409)
