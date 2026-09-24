import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import EnterpriseIdentityConfig, EnterpriseIdentityFlow, OrganizationMembership
from .models import AuditEvent, Organization


class EnterpriseIdentityTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Identity Workspace")
        self.owner = User.objects.create_user(
            username="identity-owner",
            email="owner@example.com",
            password="test-password-long",
        )
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.member = User.objects.create_user(
            username="identity-member",
            email="member@example.com",
            password="test-password-long",
        )
        OrganizationMembership.objects.create(
            user=self.member,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        self.client = APIClient()

    def _configure_oidc(self, domain="example.com", enabled=True):
        self.client.force_authenticate(self.owner)
        return self.client.put(
            "/api/enterprise-identity/",
            {
                "enabled": enabled,
                "provider": "oidc",
                "email_domain": domain,
                "issuer_url": "https://idp.example.test/",
                "client_id": "finopser-test-client",
                "secret_reference": "env://FINOPSER_OIDC_CLIENT_SECRET",
            },
            format="json",
        )

    def test_configuration_is_disabled_until_created(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/enterprise-identity/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["configured"])
        self.assertFalse(response.data["enabled"])
        self.assertIsNone(response.data["provider"])

    def test_owner_can_configure_oidc_without_exposing_secret_reference(self):
        response = self._configure_oidc()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["configured"])
        self.assertTrue(response.data["enabled"])
        self.assertEqual(response.data["provider"], "oidc")
        self.assertEqual(response.data["email_domain"], "example.com")
        self.assertTrue(response.data["secret_reference_configured"])
        self.assertNotIn("secret_reference", response.data)
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="enterprise_identity.configure",
            ).exists()
        )

    def test_member_cannot_change_enterprise_identity_configuration(self):
        self.client.force_authenticate(self.member)
        response = self.client.put(
            "/api/enterprise-identity/",
            {
                "enabled": False,
                "provider": "oidc",
                "email_domain": "example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(EnterpriseIdentityConfig.objects.exists())

    def test_public_discovery_returns_minimal_domain_match_only(self):
        configured = self._configure_oidc()
        self.assertEqual(configured.status_code, 200)
        self.client.force_authenticate(user=None)

        match = self.client.post(
            "/api/auth/sso/discover/",
            {"email": "someone@EXAMPLE.COM"},
            format="json",
        )
        missing = self.client.post(
            "/api/auth/sso/discover/",
            {"email": "someone@unknown.test"},
            format="json",
        )

        self.assertEqual(match.status_code, 200)
        self.assertEqual(match.data, {"sso_available": True, "provider": "oidc"})
        self.assertEqual(missing.data, {"sso_available": False, "provider": None})
        self.assertNotIn("organization", match.data)

    def test_email_domain_cannot_be_claimed_by_two_workspaces(self):
        first = self._configure_oidc(domain="shared.example")
        self.assertEqual(first.status_code, 200)

        other = Organization.objects.create(name="Other Identity Workspace")
        other_owner = User.objects.create_user(
            username="other-owner",
            password="test-password-long",
        )
        OrganizationMembership.objects.create(
            user=other_owner,
            organization=other,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client.force_authenticate(other_owner)
        response = self.client.put(
            "/api/enterprise-identity/",
            {
                "enabled": True,
                "provider": "oidc",
                "email_domain": "SHARED.EXAMPLE",
                "issuer_url": "https://other-idp.example.test/",
                "client_id": "other-client",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(EnterpriseIdentityConfig.objects.filter(organization=other).exists())

    def test_local_password_login_remains_available(self):
        configured = self._configure_oidc(enabled=False)
        self.assertEqual(configured.status_code, 200)
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/auth/login/",
            {"username": self.owner.username, "password": "test-password-long"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["authenticated"])


    def test_oidc_authorization_request_is_tenant_bound_pkce_and_secret_safe(self):
        configured = self._configure_oidc()
        self.assertEqual(configured.status_code, 200)
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/auth/sso/oidc/authorize/",
            {"email": "person@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "oidc")
        self.assertEqual(response.data["expires_in"], 600)
        parsed = urlparse(response.data["authorization_url"])
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "idp.example.test")
        self.assertEqual(parsed.path, "/authorize")
        self.assertEqual(query["client_id"], ["finopser-test-client"])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["scope"], ["openid email profile"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertNotIn("secret_reference", response.data["authorization_url"])
        self.assertNotIn("FINOPSER_OIDC_CLIENT_SECRET", response.data["authorization_url"])

        flow = EnterpriseIdentityFlow.objects.select_related("identity_config").get()
        self.assertEqual(flow.identity_config.organization, self.organization)
        self.assertEqual(
            flow.state_digest,
            hashlib.sha256(query["state"][0].encode()).hexdigest(),
        )
        self.assertEqual(flow.nonce, query["nonce"][0])
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(flow.pkce_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        self.assertEqual(query["code_challenge"], [expected_challenge])
        self.assertNotIn(flow.pkce_verifier, response.data["authorization_url"])
        self.assertGreater(flow.expires_at, flow.created_at)
        self.assertIsNone(flow.consumed_at)

    def test_oidc_authorization_fails_closed_for_missing_disabled_or_saml_config(self):
        self.client.force_authenticate(user=None)
        missing = self.client.post(
            "/api/auth/sso/oidc/authorize/",
            {"email": "person@missing.example"},
            format="json",
        )
        self.assertEqual(missing.status_code, 404)
        self.assertFalse(EnterpriseIdentityFlow.objects.exists())

        disabled = self._configure_oidc(domain="disabled.example", enabled=False)
        self.assertEqual(disabled.status_code, 200)
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/auth/sso/oidc/authorize/",
            {"email": "person@disabled.example"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(EnterpriseIdentityFlow.objects.exists())

        config = EnterpriseIdentityConfig.objects.get(organization=self.organization)
        config.enabled = True
        config.provider = EnterpriseIdentityConfig.Provider.SAML
        config.metadata_url = "https://idp.example.test/metadata"
        config.entity_id = "urn:finopser:test"
        config.save(update_fields=["enabled", "provider", "metadata_url", "entity_id"])
        response = self.client.post(
            "/api/auth/sso/oidc/authorize/",
            {"email": "person@disabled.example"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(EnterpriseIdentityFlow.objects.exists())
