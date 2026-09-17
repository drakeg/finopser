import hashlib

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationDigestTests(TestCase):
    def test_stored_digest_matches_copy_once_secret(self):
        organization = Organization.objects.create(name="Digest Tenant")
        owner = User.objects.create_user(username="digest-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        destination = IntegrationDestination.objects.get(pk=response.data["id"])
        expected = hashlib.sha256(response.data["signing_secret"].encode("utf-8")).hexdigest()
        self.assertEqual(destination.signing_secret_digest, expected)
