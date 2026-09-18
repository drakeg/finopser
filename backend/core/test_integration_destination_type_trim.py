from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationTypeNormalizationTests(TestCase):
    def test_destination_type_is_trimmed(self):
        organization = Organization.objects.create(name="Type Normalize Tenant")
        owner = User.objects.create_user(username="type-normalize-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "destination_type": " webhook ", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["destination_type"], "webhook")
