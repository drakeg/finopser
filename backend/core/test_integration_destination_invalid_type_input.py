from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationTypeInputTests(TestCase):
    def test_null_destination_type_is_rejected(self):
        organization = Organization.objects.create(name="Type Input Tenant")
        owner = User.objects.create_user(username="type-input-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "destination_type": None, "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
