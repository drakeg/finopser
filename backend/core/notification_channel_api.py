from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .integration_models import IntegrationDestination, NotificationChannel
from .rbac import MANAGER_ROLES, user_has_role

SUPPORTED_NOTIFICATION_EVENTS = frozenset({"cost.threshold", "governance.finding", "report.ready"})


def _manager_or_403(request):
    if not user_has_role(request.user, MANAGER_ROLES):
        return Response({"detail": "Manager access is required."}, status=403)
    return None


def _organization_or_400(request):
    organization = user_organization(request.user)
    if organization is None:
        return None, Response({"detail": "Complete organization setup first."}, status=400)
    return organization, None


def _payload(channel):
    return {
        "id": channel.id,
        "name": channel.name,
        "destination": channel.destination_id,
        "destination_name": channel.destination.name,
        "event_types": channel.event_types,
        "is_active": channel.is_active,
        "created_at": channel.created_at,
        "disabled_at": channel.disabled_at,
        "created_by": channel.created_by.get_username(),
    }


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def channels(request):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    if request.method == "GET":
        queryset = NotificationChannel.objects.select_related("destination", "created_by").filter(organization=organization)
        return Response([_payload(channel) for channel in queryset])
    name = str(request.data.get("name", "")).strip()
    if not name or len(name) > 120:
        return Response({"detail": "A channel name of 120 characters or fewer is required."}, status=400)
    destination = IntegrationDestination.objects.filter(
        organization=organization,
        pk=request.data.get("destination"),
        is_active=True,
    ).first()
    if destination is None:
        return Response({"detail": "An active integration destination is required."}, status=400)
    raw_events = request.data.get("event_types", [])
    if not isinstance(raw_events, list) or not raw_events:
        return Response({"detail": "Select at least one supported notification event."}, status=400)
    event_types = list(dict.fromkeys(str(item) for item in raw_events))
    if any(item not in SUPPORTED_NOTIFICATION_EVENTS for item in event_types):
        return Response({"detail": "Unsupported notification event type."}, status=400)
    try:
        with transaction.atomic():
            channel = NotificationChannel.objects.create(
                organization=organization,
                destination=destination,
                name=name,
                event_types=event_types,
                created_by=request.user,
            )
            record_audit(request.user, "notification_channel.create", channel, {"event_types": event_types, "destination_id": destination.id})
    except IntegrityError:
        return Response({"detail": "A notification channel with that name already exists."}, status=status.HTTP_409_CONFLICT)
    return Response(_payload(channel), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def channel_detail(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    channel = NotificationChannel.objects.select_related("destination", "created_by").filter(organization=organization, pk=pk).first()
    if channel is None:
        return Response({"detail": "Notification channel not found."}, status=404)
    return Response(_payload(channel))


def _set_active(request, pk: int, *, is_active: bool):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    with transaction.atomic():
        channel = NotificationChannel.objects.select_for_update().select_related("destination", "created_by").filter(organization=organization, pk=pk).first()
        if channel is None:
            return Response({"detail": "Notification channel not found."}, status=404)
        if is_active and not channel.destination.is_active:
            return Response({"detail": "Enable the integration destination before enabling this channel."}, status=409)
        if channel.is_active != is_active:
            channel.is_active = is_active
            channel.disabled_at = None if is_active else timezone.now()
            channel.save(update_fields=["is_active", "disabled_at"])
            record_audit(request.user, f"notification_channel.{'enable' if is_active else 'disable'}", channel)
    return Response(_payload(channel))


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def disable_channel(request, pk: int):
    return _set_active(request, pk, is_active=False)


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def enable_channel(request, pk: int):
    return _set_active(request, pk, is_active=True)
