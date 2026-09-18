import hashlib
import secrets
from urllib.parse import urlsplit

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .integration_models import IntegrationDestination
from .rbac import MANAGER_ROLES, user_has_role


def _manager_or_403(request):
    if not user_has_role(request.user, MANAGER_ROLES):
        return Response({"detail": "Manager access is required."}, status=403)
    return None


def _organization_or_400(request):
    organization = user_organization(request.user)
    if organization is None:
        return None, Response({"detail": "Complete organization setup first."}, status=400)
    return organization, None


def _payload(destination: IntegrationDestination) -> dict:
    return {
        "id": destination.id,
        "name": destination.name,
        "destination_type": destination.destination_type,
        "endpoint_url": destination.endpoint_url,
        "signing_secret_prefix": destination.signing_secret_prefix,
        "is_active": destination.is_active,
        "created_at": destination.created_at,
        "disabled_at": destination.disabled_at,
        "created_by": destination.created_by.get_username(),
    }


def _validated_endpoint(value):
    if not isinstance(value, str) or not value.strip():
        return None, "A webhook endpoint URL is required."
    endpoint = value.strip()
    if len(endpoint) > 500:
        return None, "Webhook endpoint URL must be 500 characters or fewer."
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError:
        return None, "Webhook endpoint URL is invalid."
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None, "Webhook endpoint URL must use http or https and include a host."
    if parsed.username is not None or parsed.password is not None:
        return None, "Credentials must not be embedded in webhook endpoint URLs."
    if port is not None and not 1 <= port <= 65535:
        return None, "Webhook endpoint URL has an invalid port."
    return endpoint, None


def _new_signing_material():
    plaintext = f"finopser_whsec_{secrets.token_urlsafe(32)}"
    digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    return plaintext, digest, plaintext[:16]


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def destinations(request):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error

    if request.method == "GET":
        queryset = IntegrationDestination.objects.select_related("created_by").filter(
            organization=organization
        )
        return Response([_payload(destination) for destination in queryset])

    name = str(request.data.get("name", "")).strip()
    if not name:
        return Response({"detail": "An integration destination name is required."}, status=400)
    if len(name) > 120:
        return Response({"detail": "Integration destination name must be 120 characters or fewer."}, status=400)

    destination_type = str(request.data.get("destination_type", "webhook")).strip()
    if destination_type != IntegrationDestination.DestinationType.WEBHOOK:
        return Response({"detail": "Only webhook destinations are supported."}, status=400)
    endpoint_url, endpoint_error = _validated_endpoint(request.data.get("endpoint_url"))
    if endpoint_error is not None:
        return Response({"detail": endpoint_error}, status=400)
    if IntegrationDestination.objects.filter(organization=organization, name=name).exists():
        return Response(
            {"detail": "An integration destination with that name already exists."},
            status=status.HTTP_409_CONFLICT,
        )

    plaintext, digest, prefix = _new_signing_material()
    try:
        with transaction.atomic():
            destination = IntegrationDestination.objects.create(
                organization=organization,
                name=name,
                destination_type=destination_type,
                endpoint_url=endpoint_url,
                signing_secret_digest=digest,
                signing_secret_prefix=prefix,
                created_by=request.user,
            )
            record_audit(
                request.user,
                "integration_destination.create",
                destination,
                {
                    "name": destination.name,
                    "destination_type": destination.destination_type,
                    "endpoint_url": destination.endpoint_url,
                    "signing_secret_prefix": destination.signing_secret_prefix,
                },
            )
    except IntegrityError:
        return Response({"detail": "Unable to create a unique integration destination."}, status=409)

    payload = _payload(destination)
    payload["signing_secret"] = plaintext
    payload["secret_notice"] = "Copy this signing secret now. Finopser does not display it again."
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def destination_detail(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error
    destination = IntegrationDestination.objects.select_related("created_by").filter(
        organization=organization,
        pk=pk,
    ).first()
    if destination is None:
        return Response({"detail": "Integration destination not found."}, status=404)
    return Response(_payload(destination))


def _set_destination_active(request, pk: int, *, is_active: bool):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error

    with transaction.atomic():
        destination = (
            IntegrationDestination.objects.select_for_update()
            .select_related("created_by")
            .filter(organization=organization, pk=pk)
            .first()
        )
        if destination is None:
            return Response({"detail": "Integration destination not found."}, status=404)
        if destination.is_active == is_active:
            return Response(_payload(destination))

        destination.is_active = is_active
        destination.disabled_at = None if is_active else timezone.now()
        destination.save(update_fields=["is_active", "disabled_at"])
        action = "integration_destination.enable" if is_active else "integration_destination.disable"
        record_audit(
            request.user,
            action,
            destination,
            {
                "name": destination.name,
                "destination_type": destination.destination_type,
                "endpoint_url": destination.endpoint_url,
            },
        )
    return Response(_payload(destination))


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def disable_destination(request, pk: int):
    return _set_destination_active(request, pk, is_active=False)


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def enable_destination(request, pk: int):
    return _set_destination_active(request, pk, is_active=True)
