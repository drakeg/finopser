from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationAuthenticationBoundaryTests(TestCase):
    def test_basic_session_management_path_still_requires_manager_role(self):
        organization = Organization.objects.create(name="Auth Boundary Tenant")
        member = User.objects.create_user(username="auth-boundary-member", password="test-password-long")
        OrganizationMembership.objects.create(
            user=member,
            organization=organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        client = APIClient()
        client.force_authenticate(member)
        self.assertEqual(client.get("/api/integrations/destinations/").status_code, 403)
