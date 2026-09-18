from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationAuditObjectTests(TestCase):
    def test_audit_event_targets_integration_destination(self):
        organization = Organization.objects.create(name="Audit Object Tenant")
        owner = User.objects.create_user(username="audit-object-owner", password="test-password-long")
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
        event = AuditEvent.objects.get(action="integration_destination.create")
        self.assertEqual(event.object_type, "IntegrationDestination")
        self.assertEqual(event.object_id, str(response.data["id"]))
