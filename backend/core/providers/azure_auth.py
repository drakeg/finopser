"""Validate non-secret Azure authentication configuration before any adapter is enabled.

This module deliberately does not acquire tokens or invoke Azure APIs.
"""
from dataclasses import dataclass
from uuid import UUID


class AzureAuthConfigurationError(ValueError):
    """Safe, non-secret configuration validation failure."""


@dataclass(frozen=True)
class AzureIdentityConfig:
    mode: str
    tenant_id: str
    client_id: str | None = None

    @classmethod
    def from_mapping(cls, config: dict) -> "AzureIdentityConfig":
        allowed = {"mode", "tenant_id", "client_id"}
        if not isinstance(config, dict) or set(config) - allowed:
            raise AzureAuthConfigurationError("Unsupported Azure identity configuration fields")
        mode = config.get("mode")
        if mode not in {"managed_identity", "workload_identity"}:
            raise AzureAuthConfigurationError("Azure identity mode must be managed_identity or workload_identity")
        try:
            tenant = str(UUID(str(config.get("tenant_id", ""))))
            client = config.get("client_id")
            if client is not None:
                client = str(UUID(str(client)))
        except (TypeError, ValueError, AttributeError) as exc:
            raise AzureAuthConfigurationError("Azure identity IDs must be valid UUIDs") from exc
        if mode == "workload_identity" and not client:
            raise AzureAuthConfigurationError("Workload identity requires a client ID")
        return cls(mode=mode, tenant_id=tenant, client_id=client)
