from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationBackwardCompatibilityTests(TestCase):
    def test_existing_human_token_issue_path_remains_available(self):
        organization = Organization.objects.create(name="Compatibility Tenant")
        owner = User.objects.create_user(username="compat-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/tokens/",
            {"name": "human-token", "scopes": ["accounts:read"]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["service_principal"])
        self.assertIn("token", response.data)
