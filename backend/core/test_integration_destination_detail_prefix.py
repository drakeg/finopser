from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationDetailPrefixTests(TestCase):
    def test_detail_prefix_matches_creation_prefix(self):
        organization = Organization.objects.create(name="Detail Prefix Tenant")
        owner = User.objects.create_user(username="detail-prefix-owner", password="test-password-long")
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
        detail = client.get(f"/api/integrations/destinations/{created.data['id']}/")
        self.assertEqual(detail.data["signing_secret_prefix"], created.data["signing_secret_prefix"])
