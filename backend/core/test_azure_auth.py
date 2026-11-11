from django.test import SimpleTestCase

from .providers.azure_auth import AzureAuthConfigurationError, AzureIdentityConfig


class AzureIdentityConfigurationTests(SimpleTestCase):
    TENANT = "11111111-1111-1111-1111-111111111111"
    CLIENT = "22222222-2222-2222-2222-222222222222"

    def test_managed_identity_allows_system_assigned(self):
        config = AzureIdentityConfig.from_mapping({"mode": "managed_identity", "tenant_id": self.TENANT})
        self.assertIsNone(config.client_id)
        self.assertEqual(config.tenant_id, self.TENANT)

    def test_workload_identity_requires_client_id(self):
        with self.assertRaises(AzureAuthConfigurationError):
            AzureIdentityConfig.from_mapping({"mode": "workload_identity", "tenant_id": self.TENANT})
        config = AzureIdentityConfig.from_mapping(
            {"mode": "workload_identity", "tenant_id": self.TENANT, "client_id": self.CLIENT}
        )
        self.assertEqual(config.client_id, self.CLIENT)

    def test_rejects_secret_and_token_fields(self):
        for field in ("client_secret", "access_token", "federated_token", "certificate", "password"):
            with self.subTest(field=field):
                with self.assertRaises(AzureAuthConfigurationError):
                    AzureIdentityConfig.from_mapping(
                        {"mode": "workload_identity", "tenant_id": self.TENANT,
                         "client_id": self.CLIENT, field: "sensitive"}
                    )

    def test_rejects_invalid_mode_or_ids(self):
        for config in (
            {"mode": "client_secret", "tenant_id": self.TENANT},
            {"mode": "managed_identity", "tenant_id": "invalid"},
            {"mode": "managed_identity", "tenant_id": self.TENANT, "client_id": "invalid"},
        ):
            with self.subTest(config=config):
                with self.assertRaises(AzureAuthConfigurationError):
                    AzureIdentityConfig.from_mapping(config)
