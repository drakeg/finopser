from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationPayloadTests(TestCase):
    def test_normal_payload_contains_only_expected_metadata(self):
        organization = Organization.objects.create(name="Payload Tenant")
        owner = User.objects.create_user(username="payload-owner", password="test-password-long")
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
        self.assertEqual(
            set(detail.data),
            {
                "id",
                "name",
                "destination_type",
                "endpoint_url",
                "signing_secret_prefix",
                "is_active",
                "created_at",
                "disabled_at",
                "created_by",
            },
        )
