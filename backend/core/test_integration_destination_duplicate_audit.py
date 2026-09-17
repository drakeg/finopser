from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationRejectedAuditTests(TestCase):
    def test_rejected_duplicate_does_not_create_extra_audit_event(self):
        organization = Organization.objects.create(name="Rejected Audit Tenant")
        owner = User.objects.create_user(username="rejected-audit-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        payload = {"name": "events", "endpoint_url": "https://example.test/events"}
        client.post("/api/integrations/destinations/", payload, format="json")
        client.post("/api/integrations/destinations/", payload, format="json")
        self.assertEqual(
            AuditEvent.objects.filter(
                organization=organization,
                action="integration_destination.create",
            ).count(),
            1,
        )
