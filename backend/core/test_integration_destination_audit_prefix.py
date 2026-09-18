from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationAuditPrefixTests(TestCase):
    def test_creation_audit_may_identify_non_secret_prefix_only(self):
        organization = Organization.objects.create(name="Audit Prefix Tenant")
        owner = User.objects.create_user(username="audit-prefix-owner", password="test-password-long")
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
        event = AuditEvent.objects.get(action="integration_destination.create")
        self.assertEqual(event.metadata["signing_secret_prefix"], created.data["signing_secret_prefix"])
        self.assertNotIn("signing_secret_digest", event.metadata)
