from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationCollectionMethodTests(TestCase):
    def test_collection_does_not_support_put_delete_or_patch(self):
        organization = Organization.objects.create(name="Collection Method Tenant")
        owner = User.objects.create_user(username="collection-method-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        for method in [client.put, client.patch, client.delete]:
            response = method("/api/integrations/destinations/", {}, format="json") if method != client.delete else method("/api/integrations/destinations/")
            self.assertEqual(response.status_code, 405)
