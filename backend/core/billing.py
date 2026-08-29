from dataclasses import dataclass

from django.conf import settings

from .account_models import Subscription


class BillingError(Exception):
    pass


class BillingDisabled(BillingError):
    pass


@dataclass(frozen=True)
class BillingSession:
    url: str


class BillingProvider:
    code = "disabled"

    def create_checkout(self, subscription: Subscription, plan: str, return_url: str) -> BillingSession:
        raise BillingDisabled("Billing is not configured for this deployment.")

    def create_portal(self, subscription: Subscription, return_url: str) -> BillingSession:
        raise BillingDisabled("Billing is not configured for this deployment.")


class DisabledBillingProvider(BillingProvider):
    pass


def get_billing_provider() -> BillingProvider:
    provider = str(getattr(settings, "BILLING_PROVIDER", "")).strip().lower()
    if not provider or provider == "disabled":
        return DisabledBillingProvider()
    raise BillingError(f"Unsupported billing provider: {provider}")


def billing_provider_configured() -> bool:
    return not isinstance(get_billing_provider(), DisabledBillingProvider)
