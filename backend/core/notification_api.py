from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .account_models import Notification
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


def _serialize(notification: Notification):
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
        "is_read": notification.is_read,
        "read_at": notification.read_at,
        "first_seen": notification.first_seen,
        "last_seen": notification.last_seen,
        "occurrence_count": notification.occurrence_count,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    queryset = _queryset_for_user(request.user)
    unread = str(request.query_params.get("unread", "")).lower()
    if unread in {"1", "true", "yes"}:
        queryset = queryset.filter(is_read=False)
    category = str(request.query_params.get("category", "")).strip()
    severity = str(request.query_params.get("severity", "")).strip()
    if category:
        queryset = queryset.filter(category=category)
    if severity:
        queryset = queryset.filter(severity=severity)
    return Response(
        {
            "external_delivery_configured": external_delivery_configured(),
            "results": [_serialize(item) for item in queryset[:100]],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request):
    count = _queryset_for_user(request.user).filter(is_read=False).count()
    return Response({"unread": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request, pk: int):
    notification = _queryset_for_user(request.user).filter(pk=pk).first()
    if notification is None:
        return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at"])
    return Response(_serialize(notification))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_unread(request, pk: int):
    notification = _queryset_for_user(request.user).filter(pk=pk).first()
    if notification is None:
        return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
    notification.is_read = False
    notification.read_at = None
    notification.save(update_fields=["is_read", "read_at"])
    return Response(_serialize(notification))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    updated = _queryset_for_user(request.user).filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )
    return Response({"updated": updated})
