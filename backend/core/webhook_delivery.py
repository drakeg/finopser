import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass

from django.utils import timezone

from .integration_models import IntegrationDelivery, IntegrationDestination

SUPPORTED_EVENT_TYPES = frozenset({"governance.finding", "report.ready"})
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class WebhookRequest:
    url: str
    body: bytes
    headers: dict[str, str]


@dataclass(frozen=True)
class WebhookResponse:
    status_code: int


def build_webhook_request(destination, event_type, payload, signing_secret, *, event_id=None, timestamp=None):
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError("Unsupported integration event type.")
    if not destination.is_active:
        raise ValueError("Integration destination is disabled.")
    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be an object.")
    event_id = event_id or uuid.uuid4().hex
    timestamp = int(time.time() if timestamp is None else timestamp)
    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": timestamp,
        "data": payload,
    }
    body = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signed = f"{timestamp}.".encode("utf-8") + body
    signature = hmac.new(signing_secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return WebhookRequest(
        url=destination.endpoint_url,
        body=body,
        headers={
            "Content-Type": "application/json",
            "X-Finopser-Event": event_type,
            "X-Finopser-Event-Id": event_id,
            "X-Finopser-Timestamp": str(timestamp),
            "X-Finopser-Signature": f"v1={signature}",
        },
    )


def deliver_webhook(destination, event_type, payload, signing_secret, transport, *, event_id=None):
    if not isinstance(destination, IntegrationDestination):
        raise ValueError("A valid integration destination is required.")
    request = build_webhook_request(destination, event_type, payload, signing_secret, event_id=event_id)
    delivery = IntegrationDelivery.objects.create(
        organization=destination.organization,
        destination=destination,
        event_type=event_type,
        event_id=request.headers["X-Finopser-Event-Id"],
    )
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        delivery.attempt_count = attempt
        delivery.attempted_at = timezone.now()
        try:
            response = transport(request)
            delivery.response_status = int(response.status_code)
            if 200 <= delivery.response_status < 300:
                delivery.status = IntegrationDelivery.Status.SUCCEEDED
                delivery.last_error = ""
                delivery.save(update_fields=["attempt_count", "attempted_at", "response_status", "status", "last_error"])
                return delivery
            last_error = f"HTTP {delivery.response_status}"
        except Exception as exc:
            last_error = type(exc).__name__
            delivery.response_status = None
        delivery.last_error = last_error[:240]
        delivery.save(update_fields=["attempt_count", "attempted_at", "response_status", "last_error"])
    delivery.status = IntegrationDelivery.Status.FAILED
    delivery.save(update_fields=["status"])
    return delivery
