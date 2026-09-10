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
from .integration_models import ApiCredential
from .rbac import MANAGER_ROLES, user_has_role


AVAILABLE_SCOPES = tuple(dict.fromkeys(scope for _prefix, scope in READ_ONLY_API_SCOPES))


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


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def tokens(request):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization = user_organization(request.user)
    if organization is None:
        return Response({"detail": "Complete organization setup first."}, status=400)

    if request.method == "GET":
        credentials = ApiCredential.objects.select_related("created_by").filter(organization=organization)
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

    prefix = secrets.token_hex(6)
    plaintext = f"finopser_{prefix}_{secrets.token_urlsafe(32)}"
    digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    try:
        with transaction.atomic():
            credential = ApiCredential.objects.create(
                organization=organization,
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
def revoke_token(request, pk: int):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization = user_organization(request.user)
    credential = ApiCredential.objects.select_related("created_by").filter(
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
            {"name": credential.name, "token_prefix": credential.token_prefix, "scopes": credential.scopes},
        )
    return Response(_payload(credential))
