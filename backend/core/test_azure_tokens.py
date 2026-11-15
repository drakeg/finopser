from unittest.mock import Mock

from django.test import SimpleTestCase

from .providers.azure_auth import AzureAuthConfigurationError, AzureIdentityConfig
from .providers.azure_tokens import ARM_SCOPE, AzureTokenAcquisitionError, acquire_arm_token


class AzureTokenBrokerTests(SimpleTestCase):
    TENANT = "11111111-1111-1111-1111-111111111111"
    CLIENT = "22222222-2222-2222-2222-222222222222"

    def test_workload_identity_uses_tenant_and_client_without_secrets(self):
        credential = Mock()
        credential.get_token.return_value.token = "runtime-token"
        factory = Mock(return_value=credential)
        config = AzureIdentityConfig.from_mapping(
            {"mode": "workload_identity", "tenant_id": self.TENANT, "client_id": self.CLIENT}
        )
        self.assertEqual(acquire_arm_token(config, credential_factory=factory), "runtime-token")
        factory.assert_called_once_with(tenant_id=self.TENANT, client_id=self.CLIENT)
        credential.get_token.assert_called_once_with(ARM_SCOPE)
        credential.close.assert_called_once()

    def test_system_assigned_managed_identity(self):
        credential = Mock()
        credential.get_token.return_value.token = "runtime-token"
        factory = Mock(return_value=credential)
        config = AzureIdentityConfig.from_mapping({"mode": "managed_identity", "tenant_id": self.TENANT})
        acquire_arm_token(config, credential_factory=factory)
        factory.assert_called_once_with()

    def test_sdk_failure_does_not_leak_secrets(self):
        credential = Mock()
        credential.get_token.side_effect = RuntimeError("secret-bearing SDK exception")
        config = AzureIdentityConfig.from_mapping({"mode": "managed_identity", "tenant_id": self.TENANT})
        with self.assertRaises(AzureTokenAcquisitionError) as caught:
            acquire_arm_token(config, credential_factory=lambda **kwargs: credential)
        self.assertEqual(str(caught.exception), "Azure token acquisition failed")
        self.assertIsNone(caught.exception.__cause__)
        credential.close.assert_called_once()

    def test_rejects_manual_unvalidated_configuration(self):
        config = AzureIdentityConfig(mode="workload_identity", tenant_id=self.TENANT)
        with self.assertRaises(AzureAuthConfigurationError):
            acquire_arm_token(config, credential_factory=Mock())

    def test_empty_token_fails_closed(self):
        credential = Mock()
        credential.get_token.return_value.token = ""
        config = AzureIdentityConfig.from_mapping({"mode": "managed_identity", "tenant_id": self.TENANT})
        with self.assertRaises(AzureTokenAcquisitionError):
            acquire_arm_token(config, credential_factory=lambda **kwargs: credential)
