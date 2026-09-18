from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationHostValidationTests(TestCase):
    def test_endpoint_without_host_is_rejected(self):
        organization = Organization.objects.create(name="Host Validation Tenant")
        owner = User.objects.create_user(username="host-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "hostless", "endpoint_url": "https:///events"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
