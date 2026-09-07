import hashlib

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import ApiCredential
from .models import AuditEvent, CloudAccount, Organization


class ApiCredentialTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Integration Workspace")
        self.owner = User.objects.create_user(username="integration-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.member = User.objects.create_user(username="integration-member", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.member,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            name="Owned account",
            provider_account_id="111111111111",
            role_arn="arn:aws:iam::111111111111:role/FinopserReadOnly",
        )

        self.other_organization = Organization.objects.create(name="Other Integration Workspace")
        self.other_owner = User.objects.create_user(username="other-integration-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.other_owner,
            organization=self.other_organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.other_account = CloudAccount.objects.create(
            organization=self.other_organization,
            name="Other account",
            provider_account_id="222222222222",
            role_arn="arn:aws:iam::222222222222:role/FinopserReadOnly",
        )
        self.client = APIClient()

    def _issue_token(self, name="automation", scopes=None):
        self.client.force_authenticate(self.owner)
        payload = {"name": name}
        if scopes is not None:
            payload["scopes"] = scopes
        response = self.client.post("/api/integrations/tokens/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.client.force_authenticate(user=None)
        return response

    def _bearer_client(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def test_manager_issues_one_time_plaintext_token_without_persisting_secret(self):
        response = self._issue_token()
        token = response.data["token"]
        credential = ApiCredential.objects.get(pk=response.data["id"])

        self.assertTrue(token.startswith(f"finopser_{credential.token_prefix}_"))
        self.assertEqual(credential.token_digest, hashlib.sha256(token.encode("utf-8")).hexdigest())
        self.assertNotEqual(credential.token_digest, token)
        self.assertEqual(credential.scopes, ["accounts:read"])
        self.assertNotIn("token_digest", response.data)
        self.client.force_authenticate(self.owner)
        listing = self.client.get("/api/integrations/tokens/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data[0]["scopes"], ["accounts:read"])
        self.assertNotIn("token", listing.data[0])
        self.assertNotIn("token_digest", listing.data[0])
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="api_credential.create",
            ).exists()
        )

    def test_non_manager_cannot_list_or_create_tokens(self):
        self.client.force_authenticate(self.member)
        listing = self.client.get("/api/integrations/tokens/")
        creation = self.client.post("/api/integrations/tokens/", {"name": "denied"}, format="json")

        self.assertEqual(listing.status_code, 403)
        self.assertEqual(creation.status_code, 403)
        self.assertFalse(ApiCredential.objects.exists())

    def test_valid_token_reads_only_issuing_workspace_and_updates_last_used(self):
        token = self._issue_token().data["token"]
        client = self._bearer_client(token)

        response = client.get("/api/cloud-accounts/")

        self.assertEqual(response.status_code, 200)
        results = response.data if isinstance(response.data, list) else response.data["results"]
        ids = {item["id"] for item in results}
        self.assertIn(self.account.id, ids)
        self.assertNotIn(self.other_account.id, ids)
        credential = ApiCredential.objects.get(organization=self.organization, name="automation")
        self.assertIsNotNone(credential.last_used_at)

    def test_scope_limits_token_to_explicit_read_surface(self):
        token = self._issue_token(scopes=["accounts:read"]).data["token"]
        client = self._bearer_client(token)

        self.assertEqual(client.get("/api/cloud-accounts/").status_code, 200)
        self.assertEqual(client.get("/api/resources/").status_code, 401)

    def test_multiple_scopes_allow_only_selected_surfaces(self):
        token = self._issue_token(scopes=["accounts:read", "resources:read"]).data["token"]
        client = self._bearer_client(token)

        self.assertEqual(client.get("/api/cloud-accounts/").status_code, 200)
        self.assertEqual(client.get("/api/resources/").status_code, 200)
        self.assertEqual(client.get("/api/dashboard/").status_code, 401)

    def test_unknown_or_empty_scopes_are_rejected(self):
        self.client.force_authenticate(self.owner)

        unknown = self.client.post(
            "/api/integrations/tokens/",
            {"name": "unknown", "scopes": ["remediation:write"]},
            format="json",
        )
        empty = self.client.post(
            "/api/integrations/tokens/",
            {"name": "empty", "scopes": []},
            format="json",
        )

        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(empty.status_code, 400)
        self.assertFalse(ApiCredential.objects.filter(name__in=["unknown", "empty"]).exists())

    def test_api_token_is_rejected_for_mutation_and_unapproved_endpoints(self):
        token = self._issue_token().data["token"]
        client = self._bearer_client(token)

        mutation = client.post("/api/cloud-accounts/", {}, format="json")
        notifications = client.get("/api/notifications/")

        self.assertEqual(mutation.status_code, 401)
        self.assertEqual(notifications.status_code, 401)

    def test_revocation_immediately_invalidates_token_and_is_audited(self):
        issued = self._issue_token()
        token = issued.data["token"]
        bearer = self._bearer_client(token)
        self.assertEqual(bearer.get("/api/cloud-accounts/").status_code, 200)

        self.client.force_authenticate(self.owner)
        revoked = self.client.post(f"/api/integrations/tokens/{issued.data['id']}/revoke/")
        self.assertEqual(revoked.status_code, 200)
        self.assertFalse(revoked.data["is_active"])
        self.client.force_authenticate(user=None)

        self.assertEqual(bearer.get("/api/cloud-accounts/").status_code, 401)
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="api_credential.revoke",
            ).exists()
        )

    def test_token_stops_working_if_owner_leaves_issuing_workspace(self):
        token = self._issue_token().data["token"]
        bearer = self._bearer_client(token)
        OrganizationMembership.objects.filter(user=self.owner, organization=self.organization).delete()

        self.assertEqual(bearer.get("/api/cloud-accounts/").status_code, 401)

    def test_existing_session_authentication_remains_compatible(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/cloud-accounts/")

        self.assertEqual(response.status_code, 200)
