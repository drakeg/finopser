from django.conf import settings
from django.db import models

from .models import Organization


def default_api_credential_scopes():
    return ["accounts:read"]


class ServicePrincipal(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="service_principals",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_service_principals",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    disabled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_service_principal_org_name",
            )
        ]

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_superuser(self) -> bool:
        return False

    def get_username(self) -> str:
        return f"service:{self.name}"

    def __str__(self) -> str:
        state = "active" if self.is_active else "disabled"
        return f"{self.organization}: {self.name} ({state})"


class ApiCredential(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="api_credentials",
    )
    service_principal = models.ForeignKey(
        ServicePrincipal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="credentials",
    )
    name = models.CharField(max_length=120)
    token_prefix = models.CharField(max_length=24, unique=True)
    token_digest = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=default_api_credential_scopes)
    expires_at = models.DateTimeField(null=True, blank=True)
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


class IntegrationDestination(models.Model):
    class DestinationType(models.TextChoices):
        WEBHOOK = "webhook", "Webhook"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="integration_destinations",
    )
    name = models.CharField(max_length=120)
    destination_type = models.CharField(
        max_length=32,
        choices=DestinationType.choices,
        default=DestinationType.WEBHOOK,
    )
    endpoint_url = models.URLField(max_length=500)
    signing_secret_digest = models.CharField(max_length=64)
    signing_secret_prefix = models.CharField(max_length=16)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_integration_destinations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    disabled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_integration_destination_org_name",
            )
        ]

    def __str__(self) -> str:
        state = "active" if self.is_active else "disabled"
        return f"{self.organization}: {self.name} ({self.destination_type}, {state})"
