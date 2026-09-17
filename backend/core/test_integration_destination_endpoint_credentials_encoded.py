from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationEncodedCredentialsTests(TestCase):
    def test_endpoint_with_username_is_rejected_even_without_password(self):
        organization = Organization.objects.create(name="Encoded Credential Tenant")
        owner = User.objects.create_user(username="encoded-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "bad", "endpoint_url": "https://user@example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
