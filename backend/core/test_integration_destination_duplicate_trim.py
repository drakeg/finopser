from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationNormalizedDuplicateTests(TestCase):
    def test_whitespace_does_not_bypass_duplicate_name_check(self):
        organization = Organization.objects.create(name="Normalized Duplicate Tenant")
        owner = User.objects.create_user(username="normalized-duplicate-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        first = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        second = client.post(
            "/api/integrations/destinations/",
            {"name": " events ", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
