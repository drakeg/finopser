from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationEmptyListTests(TestCase):
    def test_new_tenant_has_empty_destination_list(self):
        organization = Organization.objects.create(name="Empty List Tenant")
        owner = User.objects.create_user(username="empty-list-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/integrations/destinations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
