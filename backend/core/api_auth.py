import hashlib
import hmac

from django.utils import timezone
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS

from .entitlements import user_organization
from .integration_models import ApiCredential


READ_ONLY_API_SCOPES = (
    ("/api/dashboard/", "dashboard:read"),
    ("/api/cloud-accounts/", "accounts:read"),
    ("/api/resources/", "resources:read"),
    ("/api/costs/", "costs:read"),
    ("/api/compliance/findings/", "compliance:read"),
    ("/api/policy-violations/", "policies:read"),
    ("/api/recommendations/", "recommendations:read"),
    ("/api/reports/", "reports:read"),
)
READ_ONLY_API_PREFIXES = tuple(prefix for prefix, _scope in READ_ONLY_API_SCOPES)


def required_scope(path: str) -> str | None:
    return next((scope for prefix, scope in READ_ONLY_API_SCOPES if path.startswith(prefix)), None)


class ApiTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        authorization = authentication.get_authorization_header(request).decode("utf-8")
        if not authorization:
            return None
        parts = authorization.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            return None

        if request.method not in SAFE_METHODS:
            raise AuthenticationFailed("API tokens are read-only.")
        scope = required_scope(request.path)
        if scope is None:
            raise AuthenticationFailed("API token access is not enabled for this endpoint.")

        raw_token = parts[1].strip()
        token_parts = raw_token.split("_", 2)
        if len(token_parts) != 3 or token_parts[0] != "finopser":
            raise AuthenticationFailed("Invalid API token.")
        prefix = token_parts[1]
        credential = (
            ApiCredential.objects.select_related("created_by", "organization")
            .filter(token_prefix=prefix, is_active=True)
            .first()
        )
        if credential is None:
            raise AuthenticationFailed("Invalid or revoked API token.")

        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(digest, credential.token_digest):
            raise AuthenticationFailed("Invalid API token.")
        now = timezone.now()
        if credential.expires_at is not None and credential.expires_at <= now:
            raise AuthenticationFailed("API token has expired.")
        if scope not in credential.scopes:
            raise AuthenticationFailed("API token does not have the required scope.")

        user = credential.created_by
        if not user.is_active or user_organization(user) != credential.organization:
            raise AuthenticationFailed("API token owner no longer has access to this workspace.")

        ApiCredential.objects.filter(pk=credential.pk).update(last_used_at=now)
        return user, credential

    def authenticate_header(self, request):
        return self.keyword
