from django.db import models


class Recommendation(models.Model):
    class Category(models.TextChoices):
        COST = "cost", "Cost"
        GOVERNANCE = "governance", "Governance"
        OPERATIONS = "operations", "Operations"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DISMISSED = "dismissed", "Dismissed"
        RESOLVED = "resolved", "Resolved"

    source_key = models.CharField(max_length=255, unique=True)
    source_type = models.CharField(max_length=64, db_index=True)
    category = models.CharField(max_length=32, choices=Category.choices, db_index=True)
    priority = models.CharField(max_length=16, choices=Priority.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    title = models.CharField(max_length=255)
    detail = models.TextField()
    action = models.TextField()
    estimated_monthly_savings = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    cloud_account = models.ForeignKey(
        "core.CloudAccount",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recommendations",
    )
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommendations",
    )
    resource = models.ForeignKey(
        "core.CloudResource",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommendations",
    )
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    dismissed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dismissed_recommendations",
    )

    class Meta:
        app_label = "core"
        ordering = ["status", "priority", "title"]

    def __str__(self) -> str:
        return self.title


class RecommendationRun(models.Model):
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    generated_count = models.PositiveIntegerField(default=0)
    resolved_count = models.PositiveIntegerField(default=0)
    open_count = models.PositiveIntegerField(default=0)
    dismissed_count = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "core"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Recommendation generation {self.started_at.isoformat()}"
