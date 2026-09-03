from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import EnterpriseIdentityConfig, OrganizationMembership
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
