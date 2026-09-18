from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationAuditRepresentationTests(TestCase):
    def test_audit_object_representation_does_not_contain_secret(self):
        organization = Organization.objects.create(name="Audit Repr Tenant")
        owner = User.objects.create_user(username="audit-repr-owner", password="test-password-long")
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
        self.assertNotIn(response.data["signing_secret"], event.object_repr)
        self.assertNotIn(response.data["signing_secret_prefix"], event.object_repr)
