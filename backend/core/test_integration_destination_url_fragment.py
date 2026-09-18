from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationUrlComponentTests(TestCase):
    def test_query_string_is_preserved_as_endpoint_metadata(self):
        organization = Organization.objects.create(name="URL Component Tenant")
        owner = User.objects.create_user(username="url-component-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        endpoint = "https://example.test/events?source=finopser"
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": endpoint},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["endpoint_url"], endpoint)
