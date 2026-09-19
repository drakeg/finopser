import hashlib

from .audit import record_audit
from .integration_models import IntegrationDelivery, NotificationChannel
from .webhook_delivery import deliver_webhook

SUPPORTED_NOTIFICATION_EVENTS = frozenset({"cost.threshold", "governance.finding", "report.ready"})


def notification_event_id(channel: NotificationChannel, event_type: str, source_id: str) -> str:
    material = f"{channel.organization_id}:{channel.id}:{event_type}:{source_id}".encode()
    return hashlib.sha256(material).hexdigest()


def dispatch_notification_event(
    organization,
    event_type: str,
    source_id: str,
    payload: dict,
    signing_secret_for,
    transport,
    *,
    actor=None,
):
    if event_type not in SUPPORTED_NOTIFICATION_EVENTS:
        raise ValueError("Unsupported notification event type.")
    if not source_id:
        raise ValueError("A stable notification source id is required.")
    channels = NotificationChannel.objects.select_related("destination").filter(
        organization=organization,
        is_active=True,
        destination__is_active=True,
    )
    deliveries = []
    for channel in channels:
        if event_type not in channel.event_types:
            continue
        event_id = notification_event_id(channel, event_type, source_id)
        existing = IntegrationDelivery.objects.filter(
            organization=organization,
            destination=channel.destination,
            event_id=event_id,
        ).first()
        if existing is not None:
            deliveries.append(existing)
            continue
        secret = signing_secret_for(channel.destination)
        delivery = deliver_webhook(
            channel.destination,
            event_type,
            payload,
            secret,
            transport,
            event_id=event_id,
        )
        deliveries.append(delivery)
        if actor is not None:
            record_audit(
                actor,
                "notification_channel.dispatch",
                channel,
                {
                    "delivery_id": delivery.id,
                    "event_type": event_type,
                    "event_id": event_id,
                    "status": delivery.status,
                },
            )
    return deliveries
