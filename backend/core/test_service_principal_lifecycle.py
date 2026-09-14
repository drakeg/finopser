from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import ApiCredential, ServicePrincipal
from .models import AuditEvent, CloudAccount, Organization


class ServicePrincipalLifecycleTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Service Principal Workspace")
        self.owner = User.objects.create_user(username="sp-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.member = User.objects.create_user(username="sp-member", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.member,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            name="Service account",
            provider_account_id="555555555555",
            role_arn="arn:aws:iam::555555555555:role/FinopserReadOnly",
        )

        self.other_organization = Organization.objects.create(name="Other Service Principal Workspace")
        self.other_owner = User.objects.create_user(username="sp-other-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.other_owner,
            organization=self.other_organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client = APIClient()

    def _create_principal(self, name="automation", description="CI reporting"):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/integrations/service-principals/",
            {"name": name, "description": description},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response

    def _issue_service_token(self, principal_id, name="automation-token"):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/integrations/tokens/",
            {
                "name": name,
                "service_principal": principal_id,
                "scopes": ["accounts:read"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response

    def _bearer_client(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def test_manager_can_create_list_and_inspect_service_principal(self):
        created = self._create_principal()
        principal_id = created.data["id"]

        listing = self.client.get("/api/integrations/service-principals/")
        detail = self.client.get(f"/api/integrations/service-principals/{principal_id}/")

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]["name"], "automation")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["description"], "CI reporting")
        self.assertEqual(detail.data["credentials"], [])
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="service_principal.create",
            ).exists()
        )

    def test_non_manager_cannot_manage_service_principals(self):
        self.client.force_authenticate(self.member)

        listing = self.client.get("/api/integrations/service-principals/")
        creation = self.client.post(
            "/api/integrations/service-principals/",
            {"name": "denied"},
            format="json",
        )

        self.assertEqual(listing.status_code, 403)
        self.assertEqual(creation.status_code, 403)
        self.assertFalse(ServicePrincipal.objects.filter(name="denied").exists())

    def test_principal_specific_operations_are_tenant_scoped(self):
        principal_id = self._create_principal().data["id"]
        self.client.force_authenticate(self.other_owner)

        detail = self.client.get(f"/api/integrations/service-principals/{principal_id}/")
        disable = self.client.post(f"/api/integrations/service-principals/{principal_id}/disable/")
        enable = self.client.post(f"/api/integrations/service-principals/{principal_id}/enable/")

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(disable.status_code, 404)
        self.assertEqual(enable.status_code, 404)

    def test_service_bound_token_exposes_identity_metadata_without_secret_on_listing(self):
        principal_id = self._create_principal().data["id"]
        issued = self._issue_service_token(principal_id)
        token = issued.data["token"]

        self.assertEqual(issued.data["service_principal"]["id"], principal_id)
        self.assertNotIn("token_digest", issued.data)
        credential = ApiCredential.objects.get(pk=issued.data["id"])
        self.assertEqual(credential.service_principal_id, principal_id)

        listing = self.client.get("/api/integrations/tokens/")
        self.assertEqual(listing.status_code, 200)
        listed = next(item for item in listing.data if item["id"] == credential.id)
        self.assertEqual(listed["service_principal"]["name"], "automation")
        self.assertNotIn("token", listed)
        self.assertNotIn("token_digest", listed)
        self.assertEqual(self._bearer_client(token).get("/api/v1/cloud-accounts/").status_code, 200)

    def test_cannot_bind_credential_to_other_tenant_or_disabled_principal(self):
        principal_id = self._create_principal().data["id"]
        other_principal = ServicePrincipal.objects.create(
            organization=self.other_organization,
            name="other",
            created_by=self.other_owner,
        )

        self.client.force_authenticate(self.owner)
        cross_tenant = self.client.post(
            "/api/integrations/tokens/",
            {"name": "cross-tenant", "service_principal": other_principal.id},
            format="json",
        )
        self.assertEqual(cross_tenant.status_code, 404)

        self.assertEqual(
            self.client.post(
                f"/api/integrations/service-principals/{principal_id}/disable/"
            ).status_code,
            200,
        )
        disabled = self.client.post(
            "/api/integrations/tokens/",
            {"name": "disabled", "service_principal": principal_id},
            format="json",
        )
        self.assertEqual(disabled.status_code, 409)
        self.assertFalse(ApiCredential.objects.filter(name__in=["cross-tenant", "disabled"]).exists())

    def test_disable_immediately_blocks_bound_token_and_enable_restores_it(self):
        principal_id = self._create_principal().data["id"]
        issued = self._issue_service_token(principal_id)
        token_client = self._bearer_client(issued.data["token"])
        self.assertEqual(token_client.get("/api/v1/cloud-accounts/").status_code, 200)

        self.client.force_authenticate(self.owner)
        disabled = self.client.post(
            f"/api/integrations/service-principals/{principal_id}/disable/"
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.data["is_active"])
        self.assertIsNotNone(disabled.data["disabled_at"])
        self.assertEqual(token_client.get("/api/v1/cloud-accounts/").status_code, 401)

        credential = ApiCredential.objects.get(pk=issued.data["id"])
        self.assertTrue(credential.is_active)
        self.assertIsNone(credential.revoked_at)

        enabled = self.client.post(f"/api/integrations/service-principals/{principal_id}/enable/")
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.data["is_active"])
        self.assertIsNone(enabled.data["disabled_at"])
        self.assertEqual(token_client.get("/api/v1/cloud-accounts/").status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="service_principal.disable",
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="service_principal.enable",
            ).exists()
        )

    def test_disabled_principal_credential_cannot_rotate_until_reenabled(self):
        principal_id = self._create_principal().data["id"]
        issued = self._issue_service_token(principal_id)
        credential_id = issued.data["id"]

        self.client.force_authenticate(self.owner)
        self.client.post(f"/api/integrations/service-principals/{principal_id}/disable/")
        blocked = self.client.post(
            f"/api/integrations/tokens/{credential_id}/rotate/",
            {},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)

        self.client.post(f"/api/integrations/service-principals/{principal_id}/enable/")
        rotated = self.client.post(
            f"/api/integrations/tokens/{credential_id}/rotate/",
            {},
            format="json",
        )
        self.assertEqual(rotated.status_code, 200)
        self.assertEqual(rotated.data["service_principal"]["id"], principal_id)
        self.assertIn("token", rotated.data)

    def test_existing_human_owned_token_workflow_remains_compatible(self):
        self.client.force_authenticate(self.owner)
        issued = self.client.post(
            "/api/integrations/tokens/",
            {"name": "human-owned", "scopes": ["accounts:read"]},
            format="json",
        )

        self.assertEqual(issued.status_code, 201)
        self.assertIsNone(issued.data["service_principal"])
        self.assertEqual(
            self._bearer_client(issued.data["token"]).get("/api/v1/cloud-accounts/").status_code,
            200,
        )