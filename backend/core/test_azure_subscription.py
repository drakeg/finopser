import io
import json
from unittest.mock import Mock

from django.test import SimpleTestCase

from .providers.azure_auth import AzureIdentityConfig
from .providers.azure_subscription import lookup_subscription
from .providers.base import ProviderValidationError


class AzureSubscriptionLookupTests(SimpleTestCase):
    SUB = "11111111-1111-1111-1111-111111111111"
    TENANT = "22222222-2222-2222-2222-222222222222"

    def setUp(self):
        self.config = AzureIdentityConfig.from_mapping(
            {"mode": "managed_identity", "tenant_id": self.TENANT}
        )

    def _opener(self, payload):
        response = io.BytesIO(json.dumps(payload).encode())
        response.__enter__ = Mock(return_value=response) if hasattr(response, "__dict__") else None
        return response

    def test_subscription_and_tenant_verified(self):
        payload = {"subscriptionId": self.SUB, "tenantId": self.TENANT,
                   "id": f"/subscriptions/{self.SUB}", "displayName": "Dev"}
        captured = []
        def open_request(request, timeout):
            captured.append((request.full_url, request.get_header("Authorization"), timeout))
            return io.BytesIO(json.dumps(payload).encode())
        result = lookup_subscription(self.SUB, self.config,
                                     token_provider=lambda config: "short-lived-token",
                                     opener=open_request)
        self.assertEqual(result["tenant_id"], self.TENANT)
        self.assertEqual(result["subscription_id"], self.SUB)
        self.assertIn(f"/subscriptions/{self.SUB}", captured[0][0])
        self.assertEqual(captured[0][1], "Bearer short-lived-token")
        self.assertEqual(captured[0][2], 10)

    def test_rejects_cross_tenant_and_subscription(self):
        for payload in (
            {"subscriptionId": self.SUB, "tenantId": "33333333-3333-3333-3333-333333333333"},
            {"subscriptionId": "44444444-4444-4444-4444-444444444444", "tenantId": self.TENANT},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ProviderValidationError):
                    lookup_subscription(self.SUB, self.config, token_provider=lambda config: "token",
                                        opener=lambda request, timeout: io.BytesIO(json.dumps(payload).encode()))

    def test_does_not_leak_api_error(self):
        def broken(request, timeout):
            raise RuntimeError("unexpected secret-bearing error")
        with self.assertRaises(ProviderValidationError) as caught:
            lookup_subscription(self.SUB, self.config, token_provider=lambda config: "token",
                                opener=lambda request, timeout: broken(request, timeout))
        self.assertNotIn("secret-bearing", str(caught.exception))
