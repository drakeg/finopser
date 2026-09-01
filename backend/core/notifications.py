from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from .account_models import Notification


class NotificationDeliveryError(Exception):
    pass


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool


class NotificationDeliveryProvider:
    code = "disabled"

    def deliver(self, notification: Notification) -> DeliveryResult:
        return DeliveryResult(delivered=False)


class DisabledNotificationDeliveryProvider(NotificationDeliveryProvider):
    pass


def get_notification_delivery_provider() -> NotificationDeliveryProvider:
    provider = str(getattr(settings, "NOTIFICATION_PROVIDER", "disabled")).strip().lower()
    if not provider or provider == "disabled":
        return DisabledNotificationDeliveryProvider()
    raise NotificationDeliveryError(f"Unsupported notification provider: {provider}")


def external_delivery_configured() -> bool:
    return not isinstance(get_notification_delivery_provider(), DisabledNotificationDeliveryProvider)


@transaction.atomic
def notify(
    organization,
    *,
    dedupe_key: str,
    category: str,
    severity: str,
    title: str,
    detail: str = "",
    target: str = "",
    object_type: str = "",
    object_id: str = "",
) -> tuple[Notification, bool]:
    notification = (
        Notification.objects.select_for_update()
        .filter(organization=organization, dedupe_key=dedupe_key)
        .first()
    )
    created = notification is None
    if notification is None:
        notification = Notification.objects.create(
            organization=organization,
            dedupe_key=dedupe_key,
            category=category,
            severity=severity,
            title=title,
            detail=detail,
            target=target,
            object_type=object_type,
            object_id=object_id,
        )
    else:
        notification.category = category
        notification.severity = severity
        notification.title = title
        notification.detail = detail
        notification.target = target
        notification.object_type = object_type
        notification.object_id = object_id
        notification.occurrence_count += 1
        notification.is_read = False
        notification.read_at = None
        notification.save(
            update_fields=[
                "category",
                "severity",
                "title",
                "detail",
                "target",
                "object_type",
                "object_id",
                "occurrence_count",
                "is_read",
                "read_at",
                "last_seen",
            ]
        )
    get_notification_delivery_provider().deliver(notification)
    return notification, created
