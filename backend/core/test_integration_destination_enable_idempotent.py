from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationEnableIdempotentTests(TestCase):
    def test_enabling_already_active_destination_does_not_add_audit_event(self):
        organization = Organization.objects.create(name="Enable Idempotent Tenant")
        owner = User.objects.create_user(username="enable-idempotent-owner", password="test-password-long")
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
        self.assertEqual(client.post(f"/api/integrations/destinations/{created.data['id']}/enable/").status_code, 200)
        self.assertFalse(
            AuditEvent.objects.filter(
                organization=organization,
                action="integration_destination.enable",
            ).exists()
        )
