from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationEnableAuditMetadataTests(TestCase):
    def test_enable_audit_has_no_secret_material(self):
        organization = Organization.objects.create(name="Enable Audit Tenant")
        owner = User.objects.create_user(username="enable-audit-owner", password="test-password-long")
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
        destination_id = created.data["id"]
        client.post(f"/api/integrations/destinations/{destination_id}/disable/")
        client.post(f"/api/integrations/destinations/{destination_id}/enable/")
        event = AuditEvent.objects.get(action="integration_destination.enable")
        self.assertNotIn(created.data["signing_secret"], str(event.metadata))
        self.assertNotIn("signing_secret", event.metadata)
