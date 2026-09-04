from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .account_models import EnterpriseIdentityConfig
from .audit import record_audit
from .entitlements import user_organization
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
