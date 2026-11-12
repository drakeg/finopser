"""Runtime-only Azure ARM token acquisition; never persist or return token values."""
from collections.abc import Callable

from .azure_auth import AzureAuthConfigurationError, AzureIdentityConfig

ARM_SCOPE = "https://management.azure.com/.default"


class AzureTokenAcquisitionError(RuntimeError):
    """Sanitized authentication failure; underlying SDK errors are not exposed."""


def acquire_arm_token(
    config: AzureIdentityConfig,
    *,
    credential_factory: Callable | None = None,
) -> str:
    """Acquire an ARM bearer token from the runtime identity, not supplied secrets.

    Caller must keep the returned token in process memory only. This function is
    intentionally not wired to the default disabled Azure provider registry.
    """
    if not isinstance(config, AzureIdentityConfig):
        raise AzureAuthConfigurationError("Validated Azure identity configuration required")
    # Revalidate even manually constructed dataclasses; never accept arbitrary modes.
    config = AzureIdentityConfig.from_mapping(
        {"mode": config.mode, "tenant_id": config.tenant_id, "client_id": config.client_id}
    )
    try:
        if credential_factory is None:
            from azure.identity import ManagedIdentityCredential, WorkloadIdentityCredential

            credential_factory = (
                ManagedIdentityCredential
                if config.mode == "managed_identity"
                else WorkloadIdentityCredential
            )
        kwargs = {"client_id": config.client_id} if config.client_id else {}
        if config.mode == "workload_identity":
            kwargs["tenant_id"] = config.tenant_id
        credential = credential_factory(**kwargs)
        try:
            token = credential.get_token(ARM_SCOPE)
            value = token.token
            if not isinstance(value, str) or not value:
                raise AzureTokenAcquisitionError("Azure token acquisition failed")
            return value
        finally:
            close = getattr(credential, "close", None)
            if callable(close):
                close()
    except Exception as exc:
        raise AzureTokenAcquisitionError("Azure token acquisition failed") from None
