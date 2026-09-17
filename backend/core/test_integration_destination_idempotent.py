from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationIdempotentTests(TestCase):
    def test_repeated_disable_does_not_duplicate_audit_transition(self):
        organization = Organization.objects.create(name="Idempotent Tenant")
        owner = User.objects.create_user(username="idempotent-owner", password="test-password-long")
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
        self.assertEqual(client.post(f"/api/integrations/destinations/{destination_id}/disable/").status_code, 200)
        self.assertEqual(client.post(f"/api/integrations/destinations/{destination_id}/disable/").status_code, 200)
        self.assertEqual(
            AuditEvent.objects.filter(
                organization=organization,
                action="integration_destination.disable",
            ).count(),
            1,
        )
