from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationManagerDetailTests(TestCase):
    def test_member_cannot_inspect_destination(self):
        organization = Organization.objects.create(name="Manager Detail Tenant")
        owner = User.objects.create_user(username="manager-detail-owner", password="test-password-long")
        member = User.objects.create_user(username="manager-detail-member", password="test-password-long")
        for user, role in [(owner, OrganizationMembership.Role.OWNER), (member, OrganizationMembership.Role.MEMBER)]:
            OrganizationMembership.objects.create(user=user, organization=organization, role=role)
        destination = IntegrationDestination.objects.create(
            organization=organization,
            name="events",
            endpoint_url="https://example.test/events",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="prefix",
            created_by=owner,
        )
        client = APIClient()
        client.force_authenticate(member)
        self.assertEqual(client.get(f"/api/integrations/destinations/{destination.id}/").status_code, 403)
