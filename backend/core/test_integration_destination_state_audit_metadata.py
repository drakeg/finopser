from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationStateAuditMetadataTests(TestCase):
    def test_disable_audit_identifies_destination_without_secret(self):
        organization = Organization.objects.create(name="State Audit Metadata Tenant")
        owner = User.objects.create_user(username="state-audit-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        created = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        client.post(f"/api/integrations/destinations/{created.data['id']}/disable/")
        event = AuditEvent.objects.get(action="integration_destination.disable")
        self.assertEqual(event.metadata["name"], "events")
        self.assertEqual(event.metadata["destination_type"], "webhook")
        self.assertNotIn(created.data["signing_secret"], str(event.metadata))
