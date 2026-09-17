import hashlib
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api_auth import READ_ONLY_API_SCOPES
from .audit import record_audit
from .entitlements import user_organization
from .integration_models import ApiCredential, ServicePrincipal
from .rbac import MANAGER_ROLES, user_has_role


AVAILABLE_SCOPES = tuple(dict.fromkeys(scope for _prefix, scope in READ_ONLY_API_SCOPES))


def _service_principal_payload(principal: ServicePrincipal) -> dict:
    return {
        "id": principal.id,
        "name": principal.name,
        "description": principal.description,
        "is_active": principal.is_active,
        "created_at": principal.created_at,
        "disabled_at": principal.disabled_at,
        "created_by": principal.created_by.get_username(),
    }


def _payload(credential: ApiCredential) -> dict:
    return {
        "id": credential.id,
        "name": credential.name,
        "token_prefix": credential.token_prefix,
        "scopes": credential.scopes,
        "expires_at": credential.expires_at,
        "is_active": credential.is_active,
        "last_used_at": credential.last_used_at,
        "created_at": credential.created_at,
        "revoked_at": credential.revoked_at,
        "created_by": credential.created_by.get_username(),
        "service_principal": (
            _service_principal_payload(credential.service_principal)
            if credential.service_principal is not None
            else None
        ),
    }


def _manager_or_403(request):
    if not user_has_role(request.user, MANAGER_ROLES):
        return Response({"detail": "Manager access is required."}, status=403)
    return None


def _validated_scopes(value) -> list[str] | None:
    if value is None:
        return ["accounts:read"]
    if not isinstance(value, list) or not value:
        return None
    scopes = list(dict.fromkeys(str(scope).strip() for scope in value))
    if any(not scope or scope not in AVAILABLE_SCOPES for scope in scopes):
        return None
    return scopes


def _validated_expiration(value):
    if value in (None, ""):
        return None, None
    if not isinstance(value, str):
        return None, "Expiration must be an ISO 8601 date-time."
    expires_at = parse_datetime(value.strip())
    if expires_at is None or timezone.is_naive(expires_at):
        return None, "Expiration must be an ISO 8601 date-time with a timezone."
    if expires_at <= timezone.now():
        return None, "Expiration must be in the future."
    return expires_at, None


def _new_token_material():
    prefix = secrets.token_hex(6)
    plaintext = f"finopser_{prefix}_{secrets.token_urlsafe(32)}"
    digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    return prefix, plaintext, digest


def _organization_or_400(request):
    organization = user_organization(request.user)
    if organization is None:
        return None, Response({"detail": "Complete organization setup first."}, status=400)
    return organization, None


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def service_principals(request):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error

    if request.method == "GET":
        principals = ServicePrincipal.objects.select_related("created_by").filter(
            organization=organization
        )
        return Response([_service_principal_payload(principal) for principal in principals])

    name = str(request.data.get("name", "")).strip()
    description = str(request.data.get("description", "")).strip()
    if not name:
        return Response({"detail": "A service principal name is required."}, status=400)
    if len(name) > 120:
        return Response({"detail": "Service principal name must be 120 characters or fewer."}, status=400)
    if ServicePrincipal.objects.filter(organization=organization, name=name).exists():
        return Response(
            {"detail": "A service principal with that name already exists."},
            status=status.HTTP_409_CONFLICT,
        )

    with transaction.atomic():
        principal = ServicePrincipal.objects.create(
            organization=organization,
            name=name,
            description=description,
            created_by=request.user,
        )
        record_audit(
            request.user,
            "service_principal.create",
            principal,
            {"name": principal.name, "description": principal.description},
        )
    return Response(_service_principal_payload(principal), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def service_principal_detail(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error

    principal = ServicePrincipal.objects.select_related("created_by").filter(
        organization=organization,
        pk=pk,
    ).first()
    if principal is None:
        return Response({"detail": "Service principal not found."}, status=404)
    payload = _service_principal_payload(principal)
    credentials = ApiCredential.objects.select_related("created_by", "service_principal").filter(
        organization=organization,
        service_principal=principal,
    )
    payload["credentials"] = [_payload(credential) for credential in credentials]
    return Response(payload)


def _set_service_principal_active(request, pk: int, *, is_active: bool):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error

    with transaction.atomic():
        principal = (
            ServicePrincipal.objects.select_for_update()
            .select_related("created_by")
            .filter(organization=organization, pk=pk)
            .first()
        )
        if principal is None:
            return Response({"detail": "Service principal not found."}, status=404)

        if principal.is_active == is_active:
            return Response(_service_principal_payload(principal))

        principal.is_active = is_active
        principal.disabled_at = None if is_active else timezone.now()
        principal.save(update_fields=["is_active", "disabled_at"])
        action = "service_principal.enable" if is_active else "service_principal.disable"
        record_audit(
            request.user,
            action,
            principal,
            {"name": principal.name},
        )
    return Response(_service_principal_payload(principal))


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def disable_service_principal(request, pk: int):
    return _set_service_principal_active(request, pk, is_active=False)


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def enable_service_principal(request, pk: int):
    return _set_service_principal_active(request, pk, is_active=True)


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def tokens(request):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error

    if request.method == "GET":
        credentials = ApiCredential.objects.select_related("created_by", "service_principal").filter(
            organization=organization
        )
        return Response([_payload(credential) for credential in credentials])

    name = str(request.data.get("name", "")).strip()
    if not name:
        return Response({"detail": "A token name is required."}, status=400)
    if len(name) > 120:
        return Response({"detail": "Token name must be 120 characters or fewer."}, status=400)
    scopes = _validated_scopes(request.data.get("scopes"))
    if scopes is None:
        return Response(
            {"detail": "Scopes must be a non-empty list containing only supported read-only scopes."},
            status=400,
        )
    expires_at, expiration_error = _validated_expiration(request.data.get("expires_at"))
    if expiration_error is not None:
        return Response({"detail": expiration_error}, status=400)
    if ApiCredential.objects.filter(organization=organization, name=name).exists():
        return Response({"detail": "A token with that name already exists."}, status=status.HTTP_409_CONFLICT)

    service_principal = None
    service_principal_id = request.data.get("service_principal")
    if service_principal_id not in (None, ""):
        service_principal = ServicePrincipal.objects.filter(
            organization=organization,
            pk=service_principal_id,
        ).first()
        if service_principal is None:
            return Response({"detail": "Service principal not found."}, status=404)
        if not service_principal.is_active:
            return Response({"detail": "Disabled service principals cannot receive credentials."}, status=409)

    prefix, plaintext, digest = _new_token_material()
    try:
        with transaction.atomic():
            credential = ApiCredential.objects.create(
                organization=organization,
                service_principal=service_principal,
                name=name,
                token_prefix=prefix,
                token_digest=digest,
                scopes=scopes,
                expires_at=expires_at,
                created_by=request.user,
            )
            record_audit(
                request.user,
                "api_credential.create",
                credential,
                {
                    "name": credential.name,
                    "token_prefix": credential.token_prefix,
                    "scopes": scopes,
                    "expires_at": expires_at.isoformat() if expires_at is not None else None,
                    "service_principal_id": service_principal.id if service_principal is not None else None,
                },
            )
    except IntegrityError:
        return Response({"detail": "Unable to issue a unique token. Try again."}, status=409)

    payload = _payload(credential)
    payload["token"] = plaintext
    payload["token_notice"] = "Copy this token now. Finopser does not store or display it again."
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def rotate_token(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, organization_error = _organization_or_400(request)
    if organization_error is not None:
        return organization_error

    expiration_supplied = "expires_at" in request.data
    expires_at = None
    if expiration_supplied:
        expires_at, expiration_error = _validated_expiration(request.data.get("expires_at"))
        if expiration_error is not None:
            return Response({"detail": expiration_error}, status=400)

    prefix, plaintext, digest = _new_token_material()
    try:
        with transaction.atomic():
            credential = (
                ApiCredential.objects.select_for_update()
                .select_related("created_by", "service_principal")
                .filter(organization=organization, pk=pk)
                .first()
            )
            if credential is None:
                return Response({"detail": "API token not found."}, status=404)
            if not credential.is_active:
                return Response({"detail": "Revoked API tokens cannot be rotated."}, status=409)
            if credential.service_principal is not None and not credential.service_principal.is_active:
                return Response({"detail": "Disabled service-principal credentials cannot be rotated."}, status=409)

            previous_prefix = credential.token_prefix
            credential.token_prefix = prefix
            credential.token_digest = digest
            credential.last_used_at = None
            update_fields = ["token_prefix", "token_digest", "last_used_at"]
            if expiration_supplied:
                credential.expires_at = expires_at
                update_fields.append("expires_at")
            credential.save(update_fields=update_fields)
            record_audit(
                request.user,
                "api_credential.rotate",
                credential,
                {
                    "name": credential.name,
                    "previous_token_prefix": previous_prefix,
                    "token_prefix": credential.token_prefix,
                    "scopes": credential.scopes,
                    "expires_at": credential.expires_at.isoformat() if credential.expires_at is not None else None,
                    "service_principal_id": (
                        credential.service_principal_id
                        if credential.service_principal is not None
                        else None
                    ),
                },
            )
    except IntegrityError:
        return Response({"detail": "Unable to rotate to a unique token. Try again."}, status=409)

    payload = _payload(credential)
    payload["token"] = plaintext
    payload["token_notice"] = "Copy this replacement token now. Finopser does not store or display it again."
    return Response(payload)


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def revoke_token(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization = user_organization(request.user)
    credential = ApiCredential.objects.select_related("created_by", "service_principal").filter(
        organization=organization,
        pk=pk,
    ).first()
    if credential is None:
        return Response({"detail": "API token not found."}, status=404)
    if not credential.is_active:
        return Response(_payload(credential))

    with transaction.atomic():
        credential.is_active = False
        credential.revoked_at = timezone.now()
        credential.save(update_fields=["is_active", "revoked_at"])
        record_audit(
            request.user,
            "api_credential.revoke",
            credential,
            {
                "name": credential.name,
                "token_prefix": credential.token_prefix,
                "scopes": credential.scopes,
                "service_principal_id": (
                    credential.service_principal_id
                    if credential.service_principal is not None
                    else None
                ),
            },
        )
    return Response(_payload(credential))