from django.conf import settings
from django.db import models

from .models import Organization


class ReportSchedule(models.Model):
    class Cadence(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="report_schedules")
    name = models.CharField(max_length=120)
    report_code = models.CharField(max_length=80)
    cadence = models.CharField(max_length=16, choices=Cadence.choices)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_report_schedules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    disabled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_report_schedule_org_name",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization}: {self.name} ({self.report_code})"


class ReportGeneration(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="report_generations")
    schedule = models.ForeignKey(
        ReportSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generations",
    )
    report_code = models.CharField(max_length=80)
    status = models.CharField(max_length=16, choices=Status.choices)
    row_count = models.PositiveIntegerField(default=0)
    truncated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_report_generations",
    )

    class Meta:
        ordering = ["-generated_at", "-id"]

    def __str__(self) -> str:
        return f"{self.organization}: {self.report_code} ({self.status})"
