import base64
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import auth
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .account_models import EnterpriseIdentityConfig, EnterpriseIdentityFlow
from .audit import record_audit
from .entitlements import user_organization
from .oidc_auth import OIDCValidationError, complete_oidc_callback
from .rbac import GovernancePermission


def _normalize_domain(value: str) -> str:
    domain = value.strip().lower().lstrip("@")
    if not domain or "." not in domain or any(char.isspace() for char in domain):
        return ""
    return domain


def _config_payload(config: EnterpriseIdentityConfig | None) -> dict:
    if config is None:
        return {
            "configured": False,
            "enabled": False,
            "provider": None,
            "email_domain": "",
            "issuer_url": "",
            "client_id": "",
            "metadata_url": "",
            "entity_id": "",
            "secret_reference_configured": False,
        }
    return {
        "configured": True,
        "enabled": config.enabled,
        "provider": config.provider,
        "email_domain": config.email_domain,
        "issuer_url": config.issuer_url,
        "client_id": config.client_id,
        "metadata_url": config.metadata_url,
        "entity_id": config.entity_id,
        "secret_reference_configured": bool(config.secret_reference),
    }


def _token_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@api_view(["POST"])
@permission_classes([AllowAny])
def begin_oidc_authorization(request):
    email = str(request.data.get("email", "")).strip().lower()
    domain = email.rpartition("@")[2] if "@" in email else ""
    domain = _normalize_domain(domain)
    if not domain:
        return Response({"detail": "A valid email address is required."}, status=400)

    config = EnterpriseIdentityConfig.objects.filter(
        enabled=True,
        provider=EnterpriseIdentityConfig.Provider.OIDC,
        email_domain__iexact=domain,
    ).first()
    if config is None or not config.issuer_url or not config.client_id:
        return Response({"detail": "OIDC is not available for that email domain."}, status=404)

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    challenge = _pkce_challenge(verifier)
    redirect_uri = request.build_absolute_uri("/api/auth/sso/oidc/callback/")
    expires_at = timezone.now() + timedelta(minutes=10)

    EnterpriseIdentityFlow.objects.filter(
        identity_config=config,
        expires_at__lt=timezone.now(),
        consumed_at__isnull=True,
    ).delete()
    EnterpriseIdentityFlow.objects.create(
        identity_config=config,
        state_digest=_token_digest(state),
        nonce=nonce,
        pkce_verifier=verifier,
        redirect_uri=redirect_uri,
        expires_at=expires_at,
    )

    authorization_endpoint = f"{config.issuer_url.rstrip('/')}/authorize"
    authorization_params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    authorization_url = f"{authorization_endpoint}?{urlencode(authorization_params)}"
    return Response(
        {
            "provider": "oidc",
            "authorization_url": authorization_url,
            "expires_in": 600,
        }
    )


def _unconfigured_oidc_validator(config, code, pkce_verifier, redirect_uri):
    raise OIDCValidationError("OIDC provider validation is not configured.")


OIDC_CLAIMS_VALIDATOR = _unconfigured_oidc_validator


@api_view(["POST"])
@permission_classes([AllowAny])
def oidc_callback(request):
    state = str(request.data.get("state", ""))
    code = str(request.data.get("code", ""))
    try:
        user = complete_oidc_callback(state, code, OIDC_CLAIMS_VALIDATOR)
    except OIDCValidationError:
        return Response({"detail": "OIDC authentication failed."}, status=401)

    auth.login(request, user)
    return Response(
        {
            "authenticated": True,
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def discover(request):
    email = str(request.data.get("email", "")).strip().lower()
    domain = email.rpartition("@")[2] if "@" in email else ""
    domain = _normalize_domain(domain)
    if not domain:
        return Response({"sso_available": False, "provider": None})
    config = EnterpriseIdentityConfig.objects.filter(
        enabled=True,
        email_domain__iexact=domain,
    ).only("provider").first()
    return Response(
        {
            "sso_available": config is not None,
            "provider": config.provider if config else None,
        }
    )


@api_view(["GET", "PUT"])
@permission_classes([GovernancePermission])
def configuration(request):
    organization = user_organization(request.user)
    if organization is None:
        return Response({"detail": "Complete organization setup first."}, status=400)

    config = EnterpriseIdentityConfig.objects.filter(organization=organization).first()
    if request.method == "GET":
        return Response(_config_payload(config))

    provider = str(request.data.get("provider", "oidc")).strip().lower()
    if provider not in {EnterpriseIdentityConfig.Provider.OIDC, EnterpriseIdentityConfig.Provider.SAML}:
        return Response({"detail": "Provider must be oidc or saml."}, status=400)
    email_domain = _normalize_domain(str(request.data.get("email_domain", "")))
    if not email_domain:
        return Response({"detail": "A valid email domain is required."}, status=400)

    enabled = bool(request.data.get("enabled", False))
    issuer_url = str(request.data.get("issuer_url", "")).strip()
    client_id = str(request.data.get("client_id", "")).strip()
    metadata_url = str(request.data.get("metadata_url", "")).strip()
    entity_id = str(request.data.get("entity_id", "")).strip()
    secret_reference = str(request.data.get("secret_reference", "")).strip()

    if enabled and provider == EnterpriseIdentityConfig.Provider.OIDC and (not issuer_url or not client_id):
        return Response(
            {"detail": "Enabled OIDC requires issuer_url and client_id."},
            status=400,
        )
    if enabled and provider == EnterpriseIdentityConfig.Provider.SAML and (not metadata_url or not entity_id):
        return Response(
            {"detail": "Enabled SAML requires metadata_url and entity_id."},
            status=400,
        )

    defaults = {
        "enabled": enabled,
        "provider": provider,
        "email_domain": email_domain,
        "issuer_url": issuer_url,
        "client_id": client_id,
        "metadata_url": metadata_url,
        "entity_id": entity_id,
    }
    if "secret_reference" in request.data:
        defaults["secret_reference"] = secret_reference

    try:
        with transaction.atomic():
            config, _ = EnterpriseIdentityConfig.objects.update_or_create(
                organization=organization,
                defaults=defaults,
            )
            record_audit(
                request.user,
                "enterprise_identity.configure",
                config,
                {
                    "provider": config.provider,
                    "enabled": config.enabled,
                    "email_domain": config.email_domain,
                    "secret_reference_configured": bool(config.secret_reference),
                },
            )
    except IntegrityError:
        return Response(
            {"detail": "That email domain is already assigned to another workspace."},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(_config_payload(config))
