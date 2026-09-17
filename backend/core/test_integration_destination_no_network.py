from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationNoNetworkTests(TestCase):
    def test_creation_does_not_attempt_outbound_http(self):
        organization = Organization.objects.create(name="No Network Tenant")
        owner = User.objects.create_user(username="no-network-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        with patch("socket.create_connection", side_effect=AssertionError("network access attempted")):
            response = client.post(
                "/api/integrations/destinations/",
                {"name": "events", "endpoint_url": "https://example.test/events"},
                format="json",
            )
        self.assertEqual(response.status_code, 201)
