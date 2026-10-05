from collections.abc import Callable

from .aws import AWSProvider
from .aws_costs import fetch_aws_costs
from .azure import AzureProvider
from .base import CloudProvider, ProviderConnection


class AWSFinOpsProvider(AWSProvider):
    def fetch_costs(self, connection: ProviderConnection, *, start_date, end_date):
        return fetch_aws_costs(
            self,
            account_id=connection.provider_account_id,
            role_arn=connection.auth.get("role_arn", ""),
            external_id=connection.auth.get("external_id", ""),
            start_date=start_date,
            end_date=end_date,
        )


ProviderFactory = Callable[[], CloudProvider]
_PROVIDER_FACTORIES: dict[str, ProviderFactory] = {"aws": AWSFinOpsProvider, "azure": AzureProvider}


def register_provider(name: str, factory: ProviderFactory) -> None:
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Provider name is required")
    if normalized in _PROVIDER_FACTORIES:
        raise ValueError(f"Cloud provider already registered: {normalized}")
    _PROVIDER_FACTORIES[normalized] = factory


def get_provider(name: str) -> CloudProvider:
    normalized = name.strip().lower()
    try:
        factory = _PROVIDER_FACTORIES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported cloud provider: {normalized}") from exc
    return factory()
