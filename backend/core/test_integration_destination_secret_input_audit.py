from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationSuppliedSecretAuditTests(TestCase):
    def test_client_supplied_secret_is_never_audited(self):
        organization = Organization.objects.create(name="Supplied Secret Audit Tenant")
        owner = User.objects.create_user(username="supplied-secret-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        supplied = "do-not-store-this-secret"
        client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events", "signing_secret": supplied},
            format="json",
        )
        event = AuditEvent.objects.get(action="integration_destination.create")
        self.assertNotIn(supplied, str(event.metadata))
