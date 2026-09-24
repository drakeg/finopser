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



class AccountProvisioningPlan(models.Model):
    vending_request = models.OneToOneField(
        AccountVendingRequest,
        on_delete=models.CASCADE,
        related_name="provisioning_plan",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="account_provisioning_plans",
    )
    provider = models.CharField(max_length=32, default="disabled")
    live_provisioning = models.BooleanField(default=False)
    intent = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_account_provisioning_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.vending_request}: plan"



class AccountProvisioningExecution(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    plan = models.ForeignKey(
        AccountProvisioningPlan,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="account_provisioning_executions",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    provider = models.CharField(max_length=32, default="disabled")
    result = models.JSONField(default=dict)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_account_provisioning_executions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.plan_id}: {self.status}"
