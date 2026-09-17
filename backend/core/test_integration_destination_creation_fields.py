from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationCreationFieldTests(TestCase):
    def test_client_cannot_choose_signing_secret(self):
        organization = Organization.objects.create(name="Creation Field Tenant")
        owner = User.objects.create_user(username="creation-field-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        supplied = "client-selected-secret"
        response = client.post(
            "/api/integrations/destinations/",
            {
                "name": "events",
                "endpoint_url": "https://example.test/events",
                "signing_secret": supplied,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.data["signing_secret"], supplied)
