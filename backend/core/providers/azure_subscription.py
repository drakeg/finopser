"""Opt-in Azure ARM subscription lookup, isolated from production provider registry."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID

from .azure_auth import AzureIdentityConfig
from .azure_tokens import acquire_arm_token
from .base import ProviderValidationError

ARM_BASE = "https://management.azure.com"
API_VERSION = "2022-12-01"


def lookup_subscription(subscription_id: str, config: AzureIdentityConfig, *,
                        token_provider=acquire_arm_token, opener=urlopen) -> dict[str, str]:
    """Fetch a single subscription using a runtime token; never log token or response body.

    This helper is intentionally not registered as a live AzureAdapter. The caller
    must enforce organization authorization before supplying subscription details.
    """
    try:
        canonical_id = str(UUID(subscription_id))
        validated = AzureIdentityConfig.from_mapping(
            {"mode": config.mode, "tenant_id": config.tenant_id, "client_id": config.client_id}
        )
    except (ValueError, AttributeError, TypeError):
        raise ProviderValidationError("Azure subscription configuration is invalid") from None
    try:
        token = token_provider(validated)
        if not isinstance(token, str) or not token:
            raise ValueError("missing token")
        url = f"{ARM_BASE}/subscriptions/{quote(canonical_id, safe='')}?api-version={API_VERSION}"
        request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        with opener(request, timeout=10) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise ValueError("invalid response")
        actual_id = str(UUID(str(payload.get("subscriptionId", ""))))
        tenant_id = str(UUID(str(payload.get("tenantId", ""))))
        if actual_id != canonical_id:
            raise ProviderValidationError("Azure validation failed: subscription identity mismatch")
        if tenant_id != validated.tenant_id:
            raise ProviderValidationError("Azure validation failed: tenant identity mismatch")
        return {
            "subscription_id": actual_id,
            "tenant_id": tenant_id,
            "resource_id": str(payload.get("id", "")),
            "display_name": str(payload.get("displayName", "")),
        }
    except ProviderValidationError:
        raise
    except Exception:
        raise ProviderValidationError("Azure subscription lookup failed") from None
