from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationRequiredFieldsTests(TestCase):
    def test_name_and_endpoint_are_required(self):
        organization = Organization.objects.create(name="Required Fields Tenant")
        owner = User.objects.create_user(username="required-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        self.assertEqual(
            client.post(
                "/api/integrations/destinations/",
                {"endpoint_url": "https://example.test/events"},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            client.post(
                "/api/integrations/destinations/",
                {"name": "missing-endpoint"},
                format="json",
            ).status_code,
            400,
        )
