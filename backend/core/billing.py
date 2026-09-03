import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .account_models import BillingEvent, Subscription
from .audit import record_audit
from .models import Organization


class BillingError(Exception):
    pass


class BillingDisabled(BillingError):
    pass


class BillingSignatureError(BillingError):
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


class StripeBillingProvider(BillingProvider):
    code = "stripe"
    api_base = "https://api.stripe.com/v1"

    def __init__(self):
        self.secret_key = str(getattr(settings, "STRIPE_SECRET_KEY", "")).strip()
        self.webhook_secret = str(getattr(settings, "STRIPE_WEBHOOK_SECRET", "")).strip()
        self.price_ids = {
            Subscription.Plan.PRO: str(getattr(settings, "STRIPE_PRICE_PRO", "")).strip(),
            Subscription.Plan.BUSINESS: str(
                getattr(settings, "STRIPE_PRICE_BUSINESS", "")
            ).strip(),
        }
        if not self.secret_key.startswith("sk_test_"):
            raise BillingDisabled("Stripe test-mode secret key is not configured.")

    def _post(self, path: str, data: dict[str, str]) -> dict:
        request = urllib.request.Request(
            f"{self.api_base}/{path}",
            data=urllib.parse.urlencode(data).encode(),
            headers={
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except (urllib.error.URLError, ValueError) as exc:
            raise BillingError("Stripe request failed.") from exc

    def create_checkout(self, subscription: Subscription, plan: str, return_url: str) -> BillingSession:
        price_id = self.price_ids.get(plan, "")
        if not price_id:
            raise BillingDisabled(f"Stripe test price for {plan} is not configured.")
        if not return_url:
            raise BillingError("A return URL is required for checkout.")
        data = {
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "success_url": return_url,
            "cancel_url": return_url,
            "metadata[organization_id]": str(subscription.organization_id),
            "metadata[plan]": plan,
            "subscription_data[metadata][organization_id]": str(subscription.organization_id),
            "subscription_data[metadata][plan]": plan,
        }
        if subscription.provider_customer_id:
            data["customer"] = subscription.provider_customer_id
        payload = self._post("checkout/sessions", data)
        url = str(payload.get("url", ""))
        if not url:
            raise BillingError("Stripe checkout did not return a URL.")
        return BillingSession(url=url)

    def create_portal(self, subscription: Subscription, return_url: str) -> BillingSession:
        if not subscription.provider_customer_id:
            raise BillingError("No Stripe customer is associated with this subscription.")
        if not return_url:
            raise BillingError("A return URL is required for the billing portal.")
        payload = self._post(
            "billing_portal/sessions",
            {"customer": subscription.provider_customer_id, "return_url": return_url},
        )
        url = str(payload.get("url", ""))
        if not url:
            raise BillingError("Stripe portal did not return a URL.")
        return BillingSession(url=url)

    def verify_event(self, body: bytes, signature_header: str, tolerance: int = 300) -> dict:
        if not self.webhook_secret:
            raise BillingDisabled("Stripe webhook secret is not configured.")
        timestamp = None
        signatures = []
        for part in signature_header.split(","):
            key, _, value = part.partition("=")
            if key == "t":
                timestamp = value
            elif key == "v1":
                signatures.append(value)
        if timestamp is None or not signatures:
            raise BillingSignatureError("Invalid Stripe signature header.")
        try:
            timestamp_int = int(timestamp)
        except ValueError as exc:
            raise BillingSignatureError("Invalid Stripe signature timestamp.") from exc
        if abs(int(time.time()) - timestamp_int) > tolerance:
            raise BillingSignatureError("Stripe webhook signature is outside the allowed tolerance.")
        signed_payload = timestamp.encode() + b"." + body
        expected = hmac.new(
            self.webhook_secret.encode(), signed_payload, hashlib.sha256
        ).hexdigest()
        if not any(hmac.compare_digest(expected, signature) for signature in signatures):
            raise BillingSignatureError("Invalid Stripe webhook signature.")
        try:
            return json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BillingSignatureError("Invalid Stripe webhook payload.") from exc


def get_billing_provider() -> BillingProvider:
    provider = str(getattr(settings, "BILLING_PROVIDER", "")).strip().lower()
    if not provider or provider == "disabled":
        return DisabledBillingProvider()
    if provider == "stripe":
        return StripeBillingProvider()
    raise BillingError(f"Unsupported billing provider: {provider}")


def billing_provider_configured() -> bool:
    try:
        return not isinstance(get_billing_provider(), DisabledBillingProvider)
    except BillingDisabled:
        return False


def _datetime_from_unix(value):
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.get_current_timezone())


def apply_stripe_event(event: dict) -> tuple[BillingEvent, bool]:
    event_id = str(event.get("id", "")).strip()
    event_type = str(event.get("type", "")).strip()
    if not event_id or not event_type:
        raise BillingError("Stripe event id and type are required.")

    with transaction.atomic():
        existing = BillingEvent.objects.select_for_update().filter(
            provider="stripe", event_id=event_id
        ).first()
        if existing is not None:
            return existing, False

        data_object = event.get("data", {}).get("object", {})
        metadata = data_object.get("metadata") or {}
        organization_id = metadata.get("organization_id")
        organization = None
        if organization_id:
            organization = Organization.objects.filter(pk=organization_id).first()

        billing_event = BillingEvent.objects.create(
            provider="stripe",
            event_id=event_id,
            event_type=event_type,
            organization=organization,
        )
        if event_type not in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            return billing_event, True
        if organization is None:
            raise BillingError("Stripe subscription event is missing a valid organization.")

        subscription = Subscription.objects.select_for_update().get(organization=organization)
        plan = str(metadata.get("plan", "")).lower()
        if plan not in {Subscription.Plan.PRO, Subscription.Plan.BUSINESS}:
            raise BillingError("Stripe subscription event contains an invalid plan.")
        stripe_status = str(data_object.get("status", "")).lower()
        status_map = {
            "trialing": Subscription.Status.TRIALING,
            "active": Subscription.Status.ACTIVE,
            "past_due": Subscription.Status.PAST_DUE,
            "canceled": Subscription.Status.CANCELED,
            "unpaid": Subscription.Status.CANCELED,
            "incomplete_expired": Subscription.Status.CANCELED,
        }
        mapped_status = status_map.get(stripe_status)
        if event_type == "customer.subscription.deleted":
            mapped_status = Subscription.Status.CANCELED
        if mapped_status is None:
            raise BillingError(f"Unsupported Stripe subscription status: {stripe_status}")

        subscription.plan = plan
        subscription.status = mapped_status
        subscription.billing_provider = "stripe"
        subscription.provider_customer_id = str(data_object.get("customer", ""))
        subscription.provider_subscription_id = str(data_object.get("id", ""))
        subscription.current_period_end = _datetime_from_unix(data_object.get("current_period_end"))
        subscription.save(
            update_fields=[
                "plan",
                "status",
                "billing_provider",
                "provider_customer_id",
                "provider_subscription_id",
                "current_period_end",
                "updated_at",
            ]
        )
        record_audit(
            None,
            f"billing.{event_type}",
            subscription,
            {
                "provider": "stripe",
                "provider_event_id": billing_event.event_id,
                "plan": subscription.plan,
                "status": subscription.status,
            },
        )
        return billing_event, True
