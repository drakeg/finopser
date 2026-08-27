from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ValidationResult:
    provider_account_id: str
    arn: str
    metadata: dict[str, str]


class ProviderValidationError(Exception):
    """Safe, user-displayable provider validation failure."""


class CloudProvider(Protocol):
    def validate_account(self, *, account_id: str, role_arn: str, external_id: str = "") -> ValidationResult:
        ...
