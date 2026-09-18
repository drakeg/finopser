from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationAuditTenantTests(TestCase):
    def test_creation_audit_is_tenant_scoped(self):
        organization = Organization.objects.create(name="Audit Tenant Scope")
        owner = User.objects.create_user(username="audit-scope-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        event = AuditEvent.objects.get(action="integration_destination.create")
        self.assertEqual(event.organization_id, organization.id)
        self.assertEqual(event.metadata["organization_id"], organization.id)
