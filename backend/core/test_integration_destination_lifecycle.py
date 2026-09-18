from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import AuditEvent, Organization


class IntegrationDestinationLifecycleTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Destination Tenant")
        self.owner = User.objects.create_user(username="destination-owner", password="test-password-long")
        self.member = User.objects.create_user(username="destination-member", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            user=self.member,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        self.other_organization = Organization.objects.create(name="Other Destination Tenant")
        self.other_owner = User.objects.create_user(username="other-destination-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.other_owner,
            organization=self.other_organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def create_destination(self):
        return self.client.post(
            "/api/integrations/destinations/",
            {
                "name": "governance-hook",
                "destination_type": "webhook",
                "endpoint_url": "https://example.test/finopser/events",
            },
            format="json",
        )

    def test_manager_can_create_list_inspect_disable_and_enable(self):
        created = self.create_destination()
        self.assertEqual(created.status_code, 201)
        self.assertIn("signing_secret", created.data)
        secret = created.data["signing_secret"]
        destination_id = created.data["id"]

        listed = self.client.get("/api/integrations/destinations/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertNotIn("signing_secret", listed.data[0])
        self.assertNotIn(secret, str(listed.data[0]))

        detail = self.client.get(f"/api/integrations/destinations/{destination_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("signing_secret", detail.data)

        disabled = self.client.post(f"/api/integrations/destinations/{destination_id}/disable/")
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.data["is_active"])
        self.assertIsNotNone(disabled.data["disabled_at"])

        enabled = self.client.post(f"/api/integrations/destinations/{destination_id}/enable/")
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.data["is_active"])
        self.assertIsNone(enabled.data["disabled_at"])

        destination = IntegrationDestination.objects.get(pk=destination_id)
        self.assertNotEqual(destination.signing_secret_digest, secret)
        self.assertNotIn(secret, destination.signing_secret_digest)

        events = AuditEvent.objects.filter(organization=self.organization)
        actions = set(events.values_list("action", flat=True))
        self.assertTrue(
            {
                "integration_destination.create",
                "integration_destination.disable",
                "integration_destination.enable",
            }.issubset(actions)
        )
        for event in events.filter(action__startswith="integration_destination."):
            self.assertNotIn(secret, str(event.metadata))

    def test_non_manager_is_forbidden(self):
        client = APIClient()
        client.force_authenticate(self.member)
        response = client.get("/api/integrations/destinations/")
        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_destination_is_opaque(self):
        destination = IntegrationDestination.objects.create(
            organization=self.other_organization,
            name="other-hook",
            endpoint_url="https://other.example.test/events",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="finopser_whsec_a",
            created_by=self.other_owner,
        )
        self.assertEqual(
            self.client.get(f"/api/integrations/destinations/{destination.id}/").status_code,
            404,
        )
        self.assertEqual(
            self.client.post(f"/api/integrations/destinations/{destination.id}/disable/").status_code,
            404,
        )

    def test_rejects_embedded_credentials_and_unsupported_types(self):
        credentials = self.client.post(
            "/api/integrations/destinations/",
            {"name": "bad", "endpoint_url": "https://user:pass@example.test/events"},
            format="json",
        )
        self.assertEqual(credentials.status_code, 400)

        unsupported = self.client.post(
            "/api/integrations/destinations/",
            {
                "name": "slack",
                "destination_type": "slack",
                "endpoint_url": "https://example.test/events",
            },
            format="json",
        )
        self.assertEqual(unsupported.status_code, 400)
