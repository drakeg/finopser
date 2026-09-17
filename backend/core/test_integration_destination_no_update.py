from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationNoUpdateTests(TestCase):
    def test_patch_is_not_supported_in_slice_one(self):
        organization = Organization.objects.create(name="No Update Tenant")
        owner = User.objects.create_user(username="no-update-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        created = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        response = client.patch(
            f"/api/integrations/destinations/{created.data['id']}/",
            {"endpoint_url": "https://example.test/changed"},
            format="json",
        )
        self.assertEqual(response.status_code, 405)
