from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationMemberMutationTests(TestCase):
    def test_member_cannot_create_destination(self):
        organization = Organization.objects.create(name="Member Mutation Tenant")
        member = User.objects.create_user(username="member-mutation", password="test-password-long")
        OrganizationMembership.objects.create(
            user=member,
            organization=organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        client = APIClient()
        client.force_authenticate(member)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
