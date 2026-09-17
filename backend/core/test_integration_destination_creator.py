from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationCreatorTests(TestCase):
    def test_creation_records_human_creator(self):
        organization = Organization.objects.create(name="Creator Tenant")
        owner = User.objects.create_user(username="creator-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_by"], owner.get_username())
