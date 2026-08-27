from django.conf import settings
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class OrganizationNode(models.Model):
    class NodeType(models.TextChoices):
        BUSINESS_UNIT = "business_unit", "Business unit"
        DEPARTMENT = "department", "Department"
        TEAM = "team", "Team"
        ENVIRONMENT = "environment", "Environment"
        OTHER = "other", "Other"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="nodes")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    name = models.CharField(max_length=200)
    node_type = models.CharField(max_length=32, choices=NodeType.choices, default=NodeType.OTHER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "parent", "name"], name="uniq_org_parent_node_name")]

    def __str__(self) -> str:
        return self.name


class Project(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="projects")
    node = models.ForeignKey(OrganizationNode, on_delete=models.PROTECT, related_name="projects")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "name"], name="uniq_project_name_per_org")]

    def __str__(self) -> str:
        return self.name


class CloudAccount(models.Model):
    class Provider(models.TextChoices):
        AWS = "aws", "Amazon Web Services"

    class Status(models.TextChoices):
        UNVALIDATED = "unvalidated", "Unvalidated"
        VALID = "valid", "Valid"
        INVALID = "invalid", "Invalid"

    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.AWS)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="cloud_accounts")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="cloud_accounts")
    name = models.CharField(max_length=200)
    provider_account_id = models.CharField(max_length=64)
    role_arn = models.CharField(max_length=512)
    external_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.UNVALIDATED)
    last_validated_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider", "provider_account_id"], name="uniq_provider_account_id")]

    def __str__(self) -> str:
        return f"{self.name} ({self.provider_account_id})"


class CloudResource(models.Model):
    provider = models.CharField(max_length=32)
    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, related_name="resources")
    provider_resource_id = models.CharField(max_length=1024)
    resource_type = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=512, blank=True)
    region = models.CharField(max_length=64, blank=True, db_index=True)
    state = models.CharField(max_length=128, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["resource_type", "name", "provider_resource_id"]
        constraints = [models.UniqueConstraint(fields=["provider", "cloud_account", "provider_resource_id"], name="uniq_cloud_resource_identity")]

    def __str__(self) -> str:
        return self.name or self.provider_resource_id


class InventorySync(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, related_name="inventory_syncs")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    discovered_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    stale_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.cloud_account} inventory {self.status}"


class CostRecord(models.Model):
    provider = models.CharField(max_length=32)
    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, related_name="cost_records")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="cost_records")
    provider_account_id = models.CharField(max_length=64)
    usage_date = models.DateField(db_index=True)
    service = models.CharField(max_length=255, db_index=True)
    region = models.CharField(max_length=64, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=16, default="USD")
    updated_at = models.DateTimeField()

    class Meta:
        ordering = ["usage_date", "service", "region"]
        constraints = [models.UniqueConstraint(fields=["cloud_account", "usage_date", "service", "region", "currency"], name="uniq_cost_record_dimension")]

    def __str__(self) -> str:
        return f"{self.usage_date} {self.service} {self.amount} {self.currency}"


class CostSync(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, related_name="cost_syncs")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.cloud_account} costs {self.status}"


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}:{self.object_id}"
