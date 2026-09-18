from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationEndpointLengthTests(TestCase):
    def test_endpoint_over_500_characters_is_rejected(self):
        organization = Organization.objects.create(name="Endpoint Length Tenant")
        owner = User.objects.create_user(username="endpoint-length-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        endpoint = "https://example.test/" + ("x" * 500)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "too-long", "endpoint_url": endpoint},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
