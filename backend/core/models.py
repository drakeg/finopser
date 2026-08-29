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


class ComplianceFramework(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} {self.version}".strip()


class ComplianceControl(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    framework = models.ForeignKey(ComplianceFramework, on_delete=models.CASCADE, related_name="controls")
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices)
    resource_type = models.CharField(max_length=128, db_index=True)
    check_key = models.CharField(max_length=100)

    class Meta:
        ordering = ["framework__code", "code"]
        constraints = [models.UniqueConstraint(fields=["framework", "code"], name="uniq_compliance_control_code")]

    def __str__(self) -> str:
        return f"{self.framework.code}:{self.code}"


class ComplianceFinding(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        EXCEPTED = "excepted", "Excepted"

    control = models.ForeignKey(ComplianceControl, on_delete=models.CASCADE, related_name="findings")
    resource = models.ForeignKey(CloudResource, on_delete=models.CASCADE, related_name="compliance_findings")
    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, related_name="compliance_findings")
    severity = models.CharField(max_length=16, choices=ComplianceControl.Severity.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    evidence = models.JSONField(default=dict, blank=True)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "severity", "control__code", "resource__name"]
        constraints = [models.UniqueConstraint(fields=["control", "resource"], name="uniq_compliance_finding_control_resource")]

    def __str__(self) -> str:
        return f"{self.control} {self.resource} {self.status}"


class ComplianceException(models.Model):
    control = models.ForeignKey(ComplianceControl, on_delete=models.CASCADE, related_name="exceptions")
    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, null=True, blank=True, related_name="compliance_exceptions")
    resource = models.ForeignKey(CloudResource, on_delete=models.CASCADE, null=True, blank=True, related_name="compliance_exceptions")
    reason = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Exception {self.control}"


class ComplianceRun(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="compliance_runs",
    )
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    passed_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    unknown_count = models.PositiveIntegerField(default=0)
    resolved_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Compliance evaluation {self.started_at.isoformat()}"


class GovernancePolicy(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Mode(models.TextChoices):
        OBSERVE = "observe", "Observe"
        RECOMMEND = "recommend", "Recommend"

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices)
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.OBSERVE)
    enabled = models.BooleanField(default=True, db_index=True)
    resource_type = models.CharField(max_length=128, db_index=True)
    rule_key = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name="governance_policies")
    node = models.ForeignKey(OrganizationNode, on_delete=models.CASCADE, null=True, blank=True, related_name="governance_policies")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name="governance_policies")
    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, null=True, blank=True, related_name="governance_policies")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_governance_policies")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class PolicyViolation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    policy = models.ForeignKey(GovernancePolicy, on_delete=models.CASCADE, related_name="violations")
    resource = models.ForeignKey(CloudResource, on_delete=models.CASCADE, related_name="policy_violations")
    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, related_name="policy_violations")
    severity = models.CharField(max_length=16, choices=GovernancePolicy.Severity.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    evidence = models.JSONField(default=dict, blank=True)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "severity", "policy__code", "resource__name"]
        constraints = [models.UniqueConstraint(fields=["policy", "resource"], name="uniq_policy_violation_resource")]

    def __str__(self) -> str:
        return f"{self.policy} {self.resource} {self.status}"


class PolicyRun(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="policy_runs",
    )
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    passed_count = models.PositiveIntegerField(default=0)
    violated_count = models.PositiveIntegerField(default=0)
    unknown_count = models.PositiveIntegerField(default=0)
    resolved_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Policy evaluation {self.started_at.isoformat()}"


class Budget(models.Model):
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=16, default="USD")
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=80)
    critical_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=90)
    enabled = models.BooleanField(default=True, db_index=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name="budgets")
    node = models.ForeignKey(OrganizationNode, on_delete=models.CASCADE, null=True, blank=True, related_name="budgets")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name="budgets")
    cloud_account = models.ForeignKey(CloudAccount, on_delete=models.CASCADE, null=True, blank=True, related_name="budgets")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_budgets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class BudgetAlert(models.Model):
    class Level(models.TextChoices):
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"
        EXCEEDED = "exceeded", "Exceeded"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="alerts")
    period = models.DateField(db_index=True)
    level = models.CharField(max_length=16, choices=Level.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    actual_amount = models.DecimalField(max_digits=20, decimal_places=2)
    utilization = models.DecimalField(max_digits=8, decimal_places=2)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-period", "budget__name", "level"]
        constraints = [models.UniqueConstraint(fields=["budget", "period", "level"], name="uniq_budget_alert_period_level")]

    def __str__(self) -> str:
        return f"{self.budget} {self.period} {self.level}"


class AuditEvent(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
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
