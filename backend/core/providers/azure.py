from datetime import date
from decimal import Decimal
from typing import Protocol

from .base import (
    CostRecord,
    CostResult,
    DiscoveryResult,
    ProviderConnection,
    ProviderCostError,
    ProviderDiscoveryError,
    ProviderValidationError,
    ResourceRecord,
    ValidationResult,
)


class AzureAdapter(Protocol):
    def subscription(self, subscription_id: str, auth: dict[str, str]) -> dict: ...
    def resources(self, subscription_id: str, auth: dict[str, str]) -> list[dict]: ...
    def costs(self, subscription_id: str, auth: dict[str, str], start_date: date, end_date: date) -> list[dict]: ...


class AzureProvider:
    name = "azure"

    def __init__(self, adapter: AzureAdapter):
        self.adapter = adapter

    def validate_connection(self, connection: ProviderConnection) -> ValidationResult:
        try:
            subscription = self.adapter.subscription(connection.provider_account_id, connection.auth)
        except Exception as exc:
            raise ProviderValidationError(f"Azure validation failed: {exc.__class__.__name__}") from exc
        actual_id = str(subscription.get("subscription_id", ""))
        if actual_id != connection.provider_account_id:
            raise ProviderValidationError("Azure validation failed: subscription identity mismatch")
        return ValidationResult(provider_account_id=actual_id, arn=str(subscription.get("resource_id", "")), metadata={"display_name": str(subscription.get("display_name", ""))})

    def discover_resources(self, connection: ProviderConnection) -> DiscoveryResult:
        try:
            records = self.adapter.resources(connection.provider_account_id, connection.auth)
        except Exception as exc:
            raise ProviderDiscoveryError(f"Azure inventory failed: {exc.__class__.__name__}") from exc
        resources=[]
        for item in records:
            resource_id=str(item.get("id", ""))
            if not resource_id:
                continue
            resources.append(ResourceRecord(provider_resource_id=resource_id,resource_type=str(item.get("type", "azure.resource")).lower(),name=str(item.get("name", resource_id)),region=str(item.get("location", "global")),state=str(item.get("state", "available")),metadata=dict(item.get("metadata", {})),tags={str(k):str(v) for k,v in dict(item.get("tags", {})).items()}))
        return DiscoveryResult(resources=resources)

    def fetch_costs(self, connection: ProviderConnection, *, start_date: date, end_date: date) -> CostResult:
        try:
            records=self.adapter.costs(connection.provider_account_id,connection.auth,start_date,end_date)
        except Exception as exc:
            raise ProviderCostError(f"Azure cost retrieval failed: {exc.__class__.__name__}") from exc
        return CostResult(records=[CostRecord(usage_date=item["usage_date"],provider_account_id=connection.provider_account_id,service=str(item.get("service", "")),region=str(item.get("region", "global")),amount=Decimal(str(item.get("amount", "0"))),currency=str(item.get("currency", "USD"))) for item in records])
