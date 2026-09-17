from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationAuditActorTests(TestCase):
    def test_creation_audit_records_human_actor(self):
        organization = Organization.objects.create(name="Audit Actor Tenant")
        owner = User.objects.create_user(username="audit-actor-owner", password="test-password-long")
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
        self.assertEqual(event.actor_id, owner.id)
