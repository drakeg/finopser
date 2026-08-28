from django.conf import settings
from django.db import models

from .models import CloudAccount, CloudResource
from .recommendation_models import Recommendation


class RemediationAction(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PREVIEWED = "previewed", "Previewed"
        APPROVED = "approved", "Approved"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        STALE = "stale", "Stale"
        REJECTED = "rejected", "Rejected"

    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remediation_actions",
    )
    resource = models.ForeignKey(
        CloudResource,
        on_delete=models.CASCADE,
        related_name="remediation_actions",
    )
    cloud_account = models.ForeignKey(
        CloudAccount,
        on_delete=models.CASCADE,
        related_name="remediation_actions",
    )
    action_key = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    simulation = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict)
    preview = models.JSONField(default=dict, blank=True)
    evidence_fingerprint = models.CharField(max_length=64, blank=True)
    provider_result = models.JSONField(default=dict, blank=True)
    error = models.CharField(max_length=255, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="requested_remediations",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_remediations",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executed_remediations",
    )
    executed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at", "id"]

    def __str__(self) -> str:
        return f"{self.action_key} {self.resource} {self.status}"


class RemediationEvent(models.Model):
    action = models.ForeignKey(
        RemediationAction,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=64, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.action_id}:{self.event_type}"
