from django.conf import settings
from django.db import models

from .models import Organization


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Administrator"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="uniq_user_organization_membership",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"


class Subscription(models.Model):
    class Plan(models.TextChoices):
        FREE = "free", "Free"
        PRO = "pro", "Pro"
        BUSINESS = "business", "Business"

    class Status(models.TextChoices):
        FREE = "free", "Free"
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.CharField(max_length=16, choices=Plan.choices, default=Plan.FREE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.FREE)
    billing_provider = models.CharField(max_length=32, blank=True)
    provider_customer_id = models.CharField(max_length=255, blank=True)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.organization}: {self.plan} ({self.status})"


class BillingEvent(models.Model):
    provider = models.CharField(max_length=32)
    event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=128)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billing_events",
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"],
                name="uniq_billing_provider_event",
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_id} ({self.event_type})"


class Notification(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.INFO)
    category = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    target = models.CharField(max_length=100, blank=True)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    dedupe_key = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    occurrence_count = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-last_seen", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "dedupe_key"],
                name="uniq_notification_org_dedupe",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization}: {self.title}"


class OnboardingProfile(models.Model):
    class Step(models.TextChoices):
        ORGANIZATION = "organization", "Create organization"
        CLOUD_ACCOUNT = "cloud_account", "Connect cloud account"
        VALIDATE = "validate", "Validate connection"
        SYNC = "sync", "Initial sync"
        COMPLETE = "complete", "Complete"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_profile",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_profiles",
    )
    current_step = models.CharField(
        max_length=32,
        choices=Step.choices,
        default=Step.ORGANIZATION,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user}: {self.current_step}"
