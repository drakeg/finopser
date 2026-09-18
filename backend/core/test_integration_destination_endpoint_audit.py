from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationEndpointAuditTests(TestCase):
    def test_endpoint_metadata_is_audited_without_credentials(self):
        organization = Organization.objects.create(name="Endpoint Audit Tenant")
        owner = User.objects.create_user(username="endpoint-audit-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        endpoint = "https://example.test/events"
        client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": endpoint},
            format="json",
        )
        event = AuditEvent.objects.get(action="integration_destination.create")
        self.assertEqual(event.metadata["endpoint_url"], endpoint)
