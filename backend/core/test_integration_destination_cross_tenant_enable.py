from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationCrossTenantEnableTests(TestCase):
    def test_cross_tenant_enable_returns_404(self):
        first = Organization.objects.create(name="First Tenant")
        second = Organization.objects.create(name="Second Tenant")
        first_owner = User.objects.create_user(username="first-owner", password="test-password-long")
        second_owner = User.objects.create_user(username="second-owner", password="test-password-long")
        for user, organization in [(first_owner, first), (second_owner, second)]:
            OrganizationMembership.objects.create(
                user=user,
                organization=organization,
                role=OrganizationMembership.Role.OWNER,
            )
        destination = IntegrationDestination.objects.create(
            organization=second,
            name="events",
            endpoint_url="https://example.test/events",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="prefix",
            is_active=False,
            created_by=second_owner,
        )
        client = APIClient()
        client.force_authenticate(first_owner)
        self.assertEqual(
            client.post(f"/api/integrations/destinations/{destination.id}/enable/").status_code,
            404,
        )
