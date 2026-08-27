from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ValidationResult:
    provider_account_id: str
    arn: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class ResourceRecord:
    provider_resource_id: str
    resource_type: str
    name: str
    region: str
    state: str = ""
    metadata: dict = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveryResult:
    resources: list[ResourceRecord]
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CostRecord:
    usage_date: date
    provider_account_id: str
    service: str
    region: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class CostResult:
    records: list[CostRecord]
    errors: list[str] = field(default_factory=list)


class ProviderValidationError(Exception):
    """Safe, user-displayable provider validation failure."""


class ProviderDiscoveryError(Exception):
    """Safe, user-displayable provider discovery failure."""


class ProviderCostError(Exception):
    """Safe, user-displayable provider cost retrieval failure."""


class CloudProvider(Protocol):
    def validate_account(self, *, account_id: str, role_arn: str, external_id: str = "") -> ValidationResult:
        ...

    def discover_resources(
        self,
        *,
        account_id: str,
        role_arn: str,
        external_id: str = "",
    ) -> DiscoveryResult:
        ...

    def fetch_costs(
        self,
        *,
        account_id: str,
        role_arn: str,
        start_date: date,
        end_date: date,
        external_id: str = "",
    ) -> CostResult:
        ...
