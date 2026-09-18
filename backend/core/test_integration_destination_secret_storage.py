from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationSecretStorageTests(TestCase):
    def test_plaintext_signing_secret_is_copy_once(self):
        organization = Organization.objects.create(name="Secret Storage Tenant")
        owner = User.objects.create_user(username="secret-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)

        created = client.post(
            "/api/integrations/destinations/",
            {"name": "copy-once", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        secret = created.data["signing_secret"]

        destination = IntegrationDestination.objects.get(pk=created.data["id"])
        self.assertNotEqual(destination.signing_secret_digest, secret)
        self.assertFalse(hasattr(destination, "signing_secret"))

        listed = client.get("/api/integrations/destinations/")
        detail = client.get(f"/api/integrations/destinations/{destination.id}/")
        self.assertNotIn(secret, str(listed.data))
        self.assertNotIn(secret, str(detail.data))
