from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import ApiCredential
from .models import AuditEvent, CloudAccount, Organization


class ServicePrincipalAcceptanceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Automation Acceptance")
        self.owner = User.objects.create_user(username="accept-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        CloudAccount.objects.create(
            organization=self.organization,
            name="Acceptance account",
            provider_account_id="777777777777",
            role_arn="arn:aws:iam::777777777777:role/FinopserReadOnly",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    @staticmethod
    def bearer(token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def test_complete_service_principal_credential_lifecycle(self):
        created = self.client.post(
            "/api/integrations/service-principals/",
            {"name": "nightly-export", "description": "Acceptance automation"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        principal_id = created.data["id"]

        issued = self.client.post(
            "/api/integrations/tokens/",
            {
                "name": "nightly-export-token",
                "service_principal": principal_id,
                "scopes": ["accounts:read"],
            },
            format="json",
        )
        self.assertEqual(issued.status_code, 201)
        credential_id = issued.data["id"]
        old_token = issued.data["token"]
        self.assertEqual(self.bearer(old_token).get("/api/v1/cloud-accounts/").status_code, 200)

        disabled = self.client.post(
            f"/api/integrations/service-principals/{principal_id}/disable/"
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(self.bearer(old_token).get("/api/v1/cloud-accounts/").status_code, 401)

        enabled = self.client.post(
            f"/api/integrations/service-principals/{principal_id}/enable/"
        )
        self.assertEqual(enabled.status_code, 200)
        self.assertEqual(self.bearer(old_token).get("/api/v1/cloud-accounts/").status_code, 200)

        rotated = self.client.post(
            f"/api/integrations/tokens/{credential_id}/rotate/",
            {},
            format="json",
        )
        self.assertEqual(rotated.status_code, 200)
        new_token = rotated.data["token"]
        self.assertNotEqual(old_token, new_token)
        self.assertEqual(self.bearer(old_token).get("/api/v1/cloud-accounts/").status_code, 401)
        self.assertEqual(self.bearer(new_token).get("/api/v1/cloud-accounts/").status_code, 200)

        revoked = self.client.post(f"/api/integrations/tokens/{credential_id}/revoke/")
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(self.bearer(new_token).get("/api/v1/cloud-accounts/").status_code, 401)
        self.assertFalse(ApiCredential.objects.get(pk=credential_id).is_active)

        events = AuditEvent.objects.filter(organization=self.organization).order_by("created_at")
        actions = set(events.values_list("action", flat=True))
        self.assertTrue(
            {
                "service_principal.create",
                "api_credential.create",
                "service_principal.disable",
                "service_principal.enable",
                "api_credential.rotate",
                "api_credential.revoke",
            }.issubset(actions)
        )
        credential_events = events.filter(action__startswith="api_credential.")
        for event in credential_events:
            self.assertEqual(event.metadata.get("service_principal_id"), principal_id)
            serialized = str(event.metadata)
            self.assertNotIn(old_token, serialized)
            self.assertNotIn(new_token, serialized)
