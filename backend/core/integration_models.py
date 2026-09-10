from django.conf import settings
from django.db import models

from .models import Organization


def default_api_credential_scopes():
    return ["accounts:read"]


class ApiCredential(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="api_credentials",
    )
    name = models.CharField(max_length=120)
    token_prefix = models.CharField(max_length=24, unique=True)
    token_digest = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=default_api_credential_scopes)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_api_credentials",
    )
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_api_credential_org_name",
            )
        ]

    def __str__(self) -> str:
        state = "active" if self.is_active else "revoked"
        return f"{self.organization}: {self.name} ({state})"
