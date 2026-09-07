import hashlib
import hmac

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS

from .entitlements import user_organization
from .integration_models import ApiCredential


READ_ONLY_API_PREFIXES = (
    "/api/dashboard/",
    "/api/cloud-accounts/",
    "/api/resources/",
    "/api/costs/",
    "/api/compliance/findings/",
    "/api/policy-violations/",
    "/api/recommendations/",
    "/api/reports/",
)


class ApiTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        authorization = get_authorization_header(request).decode("utf-8")
        if not authorization:
            return None
        parts = authorization.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            return None

        if request.method not in SAFE_METHODS:
            raise AuthenticationFailed("API tokens are read-only.")
        if not any(request.path.startswith(prefix) for prefix in READ_ONLY_API_PREFIXES):
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

        user = credential.created_by
        if not user.is_active or user_organization(user) != credential.organization:
            raise AuthenticationFailed("API token owner no longer has access to this workspace.")

        ApiCredential.objects.filter(pk=credential.pk).update(last_used_at=timezone.now())
        return user, credential

    def authenticate_header(self, request):
        return self.keyword
