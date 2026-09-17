from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationAuditSanitizationTests(TestCase):
    def test_creation_audit_contains_identity_without_plaintext_secret(self):
        organization = Organization.objects.create(name="Audit Destination Tenant")
        owner = User.objects.create_user(username="audit-destination-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        created = client.post(
            "/api/integrations/destinations/",
            {"name": "audit-hook", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        secret = created.data["signing_secret"]
        event = AuditEvent.objects.get(
            organization=organization,
            action="integration_destination.create",
        )
        self.assertEqual(event.metadata["name"], "audit-hook")
        self.assertEqual(event.metadata["destination_type"], "webhook")
        self.assertNotIn(secret, str(event.metadata))
        self.assertNotIn("signing_secret", event.metadata)
