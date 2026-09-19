from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .integration_models import IntegrationDelivery, IntegrationDestination, NotificationChannel
from .notification_dispatch import SUPPORTED_NOTIFICATION_EVENTS, dispatch_notification_event
from .rbac import MANAGER_ROLES, user_has_role
from .webhook_delivery import WebhookResponse



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


def _delivery_payload(delivery):
    return {
        "id": delivery.id,
        "destination_id": delivery.destination_id,
        "event_type": delivery.event_type,
        "event_id": delivery.event_id,
        "status": delivery.status,
        "attempt_count": delivery.attempt_count,
        "response_status": delivery.response_status,
        "last_error": delivery.last_error,
        "created_at": delivery.created_at,
        "attempted_at": delivery.attempted_at,
    }


@api_view(["GET"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def channel_deliveries(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    channel = NotificationChannel.objects.select_related("destination").filter(organization=organization, pk=pk).first()
    if channel is None:
        return Response({"detail": "Notification channel not found."}, status=404)
    deliveries = IntegrationDelivery.objects.filter(organization=organization, destination=channel.destination)[:50]
    return Response([_delivery_payload(delivery) for delivery in deliveries])


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def test_channel(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    channel = NotificationChannel.objects.select_related("destination").filter(organization=organization, pk=pk).first()
    if channel is None:
        return Response({"detail": "Notification channel not found."}, status=404)
    if not channel.is_active or not channel.destination.is_active:
        return Response({"detail": "Notification channel and destination must both be active."}, status=409)
    event_type = str(request.data.get("event_type", "")).strip()
    if event_type not in channel.event_types:
        return Response({"detail": "Channel is not subscribed to that event type."}, status=400)
    source_id = str(request.data.get("source_id", "local-test")).strip() or "local-test"
    deliveries = dispatch_notification_event(
        organization,
        event_type,
        source_id,
        {"test": True, "channel_id": channel.id},
        lambda destination: "finopser_whsec_local-test-only",
        lambda webhook_request: WebhookResponse(status_code=204),
        actor=request.user,
    )
    delivery = next((item for item in deliveries if item.destination_id == channel.destination_id), None)
    if delivery is None:
        return Response({"detail": "No delivery was eligible for this channel."}, status=409)
    return Response(_delivery_payload(delivery))
