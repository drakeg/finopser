from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization


class IntegrationDestinationInvalidUrlAuditTests(TestCase):
    def test_rejected_url_does_not_create_audit_event(self):
        organization = Organization.objects.create(name="Invalid URL Audit Tenant")
        owner = User.objects.create_user(username="invalid-url-audit-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "file:///tmp/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AuditEvent.objects.filter(action="integration_destination.create").exists())
