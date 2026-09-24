from dataclasses import dataclass


class ProvisioningExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProvisioningResult:
    provider: str
    reference: str
    message: str = ""


class DisabledProvisioningAdapter:
    provider = "disabled"

    def execute(self, intent: dict) -> ProvisioningResult:
        raise ProvisioningExecutionError("Live account provisioning is disabled.")


PROVISIONING_ADAPTER = DisabledProvisioningAdapter()
