import hashlib

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import ApiCredential, ServicePrincipal
from .models import CloudAccount, Organization


class VersionedPublicApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Public API Workspace")
        self.owner = User.objects.create_user(username="public-api-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            name="Owned account",
            provider_account_id="333333333333",
            role_arn="arn:aws:iam::333333333333:role/FinopserReadOnly",
        )
        self.other_organization = Organization.objects.create(name="Other Public API Workspace")
        self.other_account = CloudAccount.objects.create(
            organization=self.other_organization,
            name="Other account",
            provider_account_id="444444444444",
            role_arn="arn:aws:iam::444444444444:role/FinopserReadOnly",
        )

    def _token_client(self, scopes):
        raw_token = "finopser_publicv1_secret"
        ApiCredential.objects.create(
            organization=self.organization,
            name="public-v1-test",
            token_prefix="publicv1",
            token_digest=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            scopes=scopes,
            created_by=self.owner,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        return client

    def _service_principal_client(self, *, active=True):
        principal = ServicePrincipal.objects.create(
            organization=self.organization,
            name="inventory-reader",
            created_by=self.owner,
            is_active=active,
            disabled_at=None if active else timezone.now(),
        )
        raw_token = "finopser_servicev1_secret"
        ApiCredential.objects.create(
            organization=self.organization,
            service_principal=principal,
            name="service-v1-test",
            token_prefix="servicev1",
            token_digest=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            scopes=["accounts:read"],
            created_by=self.owner,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        return client, principal

    def test_versioned_accounts_surface_is_tenant_scoped(self):
        client = self._token_client(["accounts:read"])

        response = client.get("/api/v1/cloud-accounts/")

        self.assertEqual(response.status_code, 200)
        results = response.data if isinstance(response.data, list) else response.data["results"]
        ids = {item["id"] for item in results}
        self.assertIn(self.account.id, ids)
        self.assertNotIn(self.other_account.id, ids)

    def test_versioned_surface_uses_existing_scope_contract(self):
        client = self._token_client(["accounts:read"])

        self.assertEqual(client.get("/api/v1/cloud-accounts/").status_code, 200)
        self.assertEqual(client.get("/api/v1/resources/").status_code, 401)

    def test_versioned_routes_are_get_only_even_for_session_users(self):
        client = APIClient()
        client.force_authenticate(self.owner)

        response = client.post("/api/v1/cloud-accounts/", {}, format="json")

        self.assertEqual(response.status_code, 405)

    def test_unversioned_application_route_remains_available(self):
        client = self._token_client(["accounts:read"])

        self.assertEqual(client.get("/api/cloud-accounts/").status_code, 200)

    def test_unknown_future_api_version_is_not_exposed(self):
        client = self._token_client(["accounts:read"])

        self.assertEqual(client.get("/api/v2/cloud-accounts/").status_code, 404)

    def test_service_principal_is_tenant_scoped_independently_of_creator(self):
        client, principal = self._service_principal_client()
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])

        response = client.get("/api/v1/cloud-accounts/")

        self.assertEqual(response.status_code, 200)
        results = response.data if isinstance(response.data, list) else response.data["results"]
        ids = {item["id"] for item in results}
        self.assertIn(self.account.id, ids)
        self.assertNotIn(self.other_account.id, ids)
        self.assertEqual(principal.get_username(), "service:inventory-reader")

    def test_disabled_service_principal_fails_closed(self):
        client, _principal = self._service_principal_client(active=False)

        response = client.get("/api/v1/cloud-accounts/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Service principal is disabled.")