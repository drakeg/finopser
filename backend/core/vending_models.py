from django.conf import settings
from django.db import models

from .models import Organization, OrganizationNode, Project


class AccountVendingRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Environment(models.TextChoices):
        DEVELOPMENT = "development", "Development"
        TEST = "test", "Test"
        STAGING = "staging", "Staging"
        PRODUCTION = "production", "Production"
        SANDBOX = "sandbox", "Sandbox"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="account_vending_requests",
    )
    organization_node = models.ForeignKey(
        OrganizationNode,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="account_vending_requests",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="account_vending_requests",
    )
    account_name = models.CharField(max_length=200)
    account_email = models.EmailField(max_length=254)
    environment = models.CharField(max_length=32, choices=Environment.choices)
    purpose = models.TextField(blank=True)
    baseline_profile = models.CharField(max_length=64, default="standard")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="account_vending_requests",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_account_vending_requests",
    )
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "account_email"],
                name="uniq_vending_org_account_email",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization}: {self.account_name} ({self.status})"
