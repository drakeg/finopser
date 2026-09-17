from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationReenableAuditTests(TestCase):
    def test_reenable_records_one_enable_audit_event(self):
        organization = Organization.objects.create(name="Reenable Tenant")
        owner = User.objects.create_user(username="reenable-owner", password="test-password-long")
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
        self.assertEqual(
            AuditEvent.objects.filter(
                organization=organization,
                action="integration_destination.enable",
            ).count(),
            1,
        )
