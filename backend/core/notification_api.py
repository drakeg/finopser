from collections import defaultdict

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .account_models import Notification, NotificationReceipt
from .audit import record_audit
from .entitlements import user_organization
from .notifications import external_delivery_configured


def _queryset_for_user(user):
    queryset = Notification.objects.select_related("organization")
    if user.is_superuser:
        return queryset
    organization = user_organization(user)
    if organization is None:
        return queryset.none()
    return queryset.filter(organization=organization)


def _serialize(notification: Notification, read_at=None):
    return {
        "id": notification.id,
        "organization": notification.organization_id,
        "severity": notification.severity,
        "category": notification.category,
        "title": notification.title,
        "detail": notification.detail,
        "target": notification.target,
        "object_type": notification.object_type,
        "object_id": notification.object_id,
        "is_read": read_at is not None,
        "read_at": read_at,
        "first_seen": notification.first_seen,
        "last_seen": notification.last_seen,
        "occurrence_count": notification.occurrence_count,
    }


def _receipt_map(user, notifications):
    ids = [item.id for item in notifications]
    if not ids:
        return {}
    return {
        receipt.notification_id: receipt.read_at
        for receipt in NotificationReceipt.objects.filter(
            user=user,
            notification_id__in=ids,
        )
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    queryset = _queryset_for_user(request.user)
    unread = str(request.query_params.get("unread", "")).lower()
    if unread in {"1", "true", "yes"}:
        queryset = queryset.exclude(receipts__user=request.user)
    category = str(request.query_params.get("category", "")).strip()
    severity = str(request.query_params.get("severity", "")).strip()
    if category:
        queryset = queryset.filter(category=category)
    if severity:
        queryset = queryset.filter(severity=severity)
    notifications = list(queryset[:100])
    receipts = _receipt_map(request.user, notifications)
    return Response(
        {
            "external_delivery_configured": external_delivery_configured(),
            "results": [_serialize(item, receipts.get(item.id)) for item in notifications],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request):
    count = _queryset_for_user(request.user).exclude(receipts__user=request.user).count()
    return Response({"unread": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request, pk: int):
    notification = _queryset_for_user(request.user).filter(pk=pk).first()
    if notification is None:
        return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
    receipt, _ = NotificationReceipt.objects.update_or_create(
        notification=notification,
        user=request.user,
        defaults={"read_at": timezone.now()},
    )
    record_audit(request.user, "notification.read", notification)
    return Response(_serialize(notification, receipt.read_at))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_unread(request, pk: int):
    notification = _queryset_for_user(request.user).filter(pk=pk).first()
    if notification is None:
        return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
    NotificationReceipt.objects.filter(notification=notification, user=request.user).delete()
    record_audit(request.user, "notification.unread", notification)
    return Response(_serialize(notification))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    notifications = list(
        _queryset_for_user(request.user).exclude(receipts__user=request.user)
    )
    now = timezone.now()
    NotificationReceipt.objects.bulk_create(
        [
            NotificationReceipt(notification=item, user=request.user, read_at=now)
            for item in notifications
        ],
        ignore_conflicts=True,
    )
    by_organization = defaultdict(list)
    for item in notifications:
        by_organization[item.organization_id].append(item)
    for items in by_organization.values():
        record_audit(
            request.user,
            "notification.mark_all_read",
            items[0],
            {"count": len(items)},
        )
    return Response({"updated": len(notifications)})
