import hashlib

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .account_models import EnterpriseIdentityFlow, EnterpriseIdentityLink


class OIDCValidationError(ValueError):
    pass


def state_digest(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()


def complete_oidc_callback(state: str, code: str, validated_claims_for):
    if not state or not code:
        raise OIDCValidationError("State and authorization code are required.")

    with transaction.atomic():
        flow = (
            EnterpriseIdentityFlow.objects.select_for_update()
            .select_related("identity_config", "identity_config__organization")
            .filter(state_digest=state_digest(state))
            .first()
        )
        now = timezone.now()
        if flow is None or flow.consumed_at is not None or flow.expires_at <= now:
            raise OIDCValidationError("OIDC flow is invalid or expired.")

        config = flow.identity_config
        if not config.enabled or config.provider != config.Provider.OIDC:
            raise OIDCValidationError("OIDC configuration is unavailable.")

        claims = validated_claims_for(config, code, flow.pkce_verifier, flow.redirect_uri)
        if not isinstance(claims, dict):
            raise OIDCValidationError("OIDC claims are invalid.")

        issuer = str(claims.get("iss", "")).rstrip("/")
        audience = claims.get("aud")
        audiences = audience if isinstance(audience, list) else [audience]
        subject = str(claims.get("sub", "")).strip()
        nonce = str(claims.get("nonce", ""))
        email = str(claims.get("email", "")).strip().lower()
        email_verified = claims.get("email_verified") is True
        expected_issuer = config.issuer_url.rstrip("/")

        if issuer != expected_issuer or config.client_id not in audiences:
            raise OIDCValidationError("OIDC issuer or audience is invalid.")
        if not subject or nonce != flow.nonce:
            raise OIDCValidationError("OIDC subject or nonce is invalid.")
        if not email_verified or email.rpartition("@")[2] != config.email_domain.lower():
            raise OIDCValidationError("OIDC email identity is invalid.")

        link = EnterpriseIdentityLink.objects.filter(
            identity_config=config,
            subject=subject,
        ).select_related("user").first()
        if link is None:
            User = get_user_model()
            matches = User.objects.filter(email__iexact=email, is_active=True)
            if matches.count() != 1:
                raise OIDCValidationError("OIDC identity is not linked to a local user.")
            user = matches.get()
            if not config.organization.memberships.filter(user=user).exists():
                raise OIDCValidationError("OIDC identity is outside the configured workspace.")
            link = EnterpriseIdentityLink.objects.create(
                identity_config=config,
                user=user,
                subject=subject,
                email=email,
            )
        elif not link.user.is_active or link.email.lower() != email:
            raise OIDCValidationError("OIDC identity link is invalid.")

        flow.consumed_at = now
        flow.save(update_fields=["consumed_at"])
        link.last_authenticated_at = now
        link.save(update_fields=["last_authenticated_at"])
        return link.user
