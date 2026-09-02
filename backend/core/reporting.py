import csv
import io
from dataclasses import asdict, dataclass

from django.utils import timezone

from .entitlements import has_feature
from .models import AuditEvent, CloudResource, ComplianceFinding, CostRecord, PolicyViolation
from .tenant_scope import scope_queryset

MAX_SYNC_ROWS = 5000


@dataclass(frozen=True)
class ReportDefinition:
    code: str
    name: str
    description: str
    format: str
    target: str
    feature: str | None = None


REPORT_CATALOG = {
    "resource-inventory": ReportDefinition(
        code="resource-inventory",
        name="Resource inventory",
        description="Normalized cloud resource inventory from persisted evidence.",
        format="csv",
        target="Resources",
    ),
    "cost-detail": ReportDefinition(
        code="cost-detail",
        name="Cost detail",
        description="Persisted cloud cost records by date, account, project, service, and region.",
        format="csv",
        target="Costs",
    ),
    "compliance-findings": ReportDefinition(
        code="compliance-findings",
        name="Compliance findings",
        description="Persisted compliance findings with framework, control, resource, severity, and status.",
        format="csv",
        target="Compliance",
        feature="compliance",
    ),
    "policy-violations": ReportDefinition(
        code="policy-violations",
        name="Policy violations",
        description="Persisted governance policy violations with resource, severity, and lifecycle state.",
        format="csv",
        target="Policies",
        feature="policies",
    ),
    "audit-events": ReportDefinition(
        code="audit-events",
        name="Audit events",
        description="Application audit events for governance-relevant and privileged actions.",
        format="csv",
        target="Admin",
    ),
}


def report_catalog(user):
    reports = []
    for definition in REPORT_CATALOG.values():
        if definition.feature and not has_feature(user, definition.feature):
            continue
        reports.append(asdict(definition))
    return reports


def report_allowed(user, code):
    definition = REPORT_CATALOG[code]
    return not definition.feature or has_feature(user, definition.feature)


def resource_inventory_queryset(user, *, account_id=None, resource_type=None, active=None):
    queryset = scope_queryset(
        CloudResource.objects.select_related("cloud_account").order_by(
            "cloud_account__name", "resource_type", "name", "provider_resource_id"
        ),
        user,
        lookup="cloud_account__organization_id",
    )
    if account_id:
        queryset = queryset.filter(cloud_account_id=account_id)
    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)
    if active is not None:
        queryset = queryset.filter(is_active=active)
    return queryset[:MAX_SYNC_ROWS]


def cost_detail_queryset(user, *, account_id=None, project_id=None, service=None, start_date=None, end_date=None):
    queryset = scope_queryset(
        CostRecord.objects.select_related("cloud_account", "project").order_by(
            "usage_date", "cloud_account__name", "service", "region", "id"
        ),
        user,
        lookup="cloud_account__organization_id",
    )
    if account_id:
        queryset = queryset.filter(cloud_account_id=account_id)
    if project_id:
        queryset = queryset.filter(project_id=project_id)
    if service:
        queryset = queryset.filter(service=service)
    if start_date:
        queryset = queryset.filter(usage_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(usage_date__lte=end_date)
    return queryset[:MAX_SYNC_ROWS]


def compliance_findings_queryset(user, *, status=None, severity=None, account_id=None):
    queryset = scope_queryset(
        ComplianceFinding.objects.select_related(
            "control__framework", "resource", "cloud_account"
        ).order_by("status", "severity", "control__framework__code", "control__code", "id"),
        user,
        lookup="cloud_account__organization_id",
    )
    if status:
        queryset = queryset.filter(status=status)
    if severity:
        queryset = queryset.filter(severity=severity)
    if account_id:
        queryset = queryset.filter(cloud_account_id=account_id)
    return queryset[:MAX_SYNC_ROWS]


def policy_violations_queryset(user, *, status=None, severity=None, account_id=None):
    queryset = scope_queryset(
        PolicyViolation.objects.select_related("policy", "resource", "cloud_account").order_by(
            "status", "severity", "policy__code", "id"
        ),
        user,
        lookup="cloud_account__organization_id",
    )
    if status:
        queryset = queryset.filter(status=status)
    if severity:
        queryset = queryset.filter(severity=severity)
    if account_id:
        queryset = queryset.filter(cloud_account_id=account_id)
    return queryset[:MAX_SYNC_ROWS]


def audit_events_queryset(user, *, action=None, object_type=None):
    queryset = scope_queryset(
        AuditEvent.objects.select_related("actor").order_by("-created_at", "-id"),
        user,
    )
    if action:
        queryset = queryset.filter(action=action)
    if object_type:
        queryset = queryset.filter(object_type=object_type)
    return queryset[:MAX_SYNC_ROWS]


def _report_result(code, output, count):
    return {
        "generated_at": timezone.now(),
        "report": REPORT_CATALOG[code],
        "row_count": count,
        "truncated": count >= MAX_SYNC_ROWS,
        "content": output.getvalue(),
    }


def build_resource_inventory_report(user, *, account_id=None, resource_type=None, active=None):
    rows = resource_inventory_queryset(
        user,
        account_id=account_id,
        resource_type=resource_type,
        active=active,
    )
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "account",
            "provider",
            "provider_resource_id",
            "resource_type",
            "name",
            "region",
            "state",
            "is_active",
            "last_seen",
        ]
    )
    count = 0
    for resource in rows:
        writer.writerow(
            [
                resource.cloud_account.name,
                resource.provider,
                resource.provider_resource_id,
                resource.resource_type,
                resource.name,
                resource.region,
                resource.state,
                "true" if resource.is_active else "false",
                resource.last_seen.isoformat(),
            ]
        )
        count += 1
    return _report_result("resource-inventory", output, count)


def build_cost_detail_report(user, *, account_id=None, project_id=None, service=None, start_date=None, end_date=None):
    rows = cost_detail_queryset(
        user,
        account_id=account_id,
        project_id=project_id,
        service=service,
        start_date=start_date,
        end_date=end_date,
    )
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "usage_date",
            "account",
            "provider_account_id",
            "project",
            "service",
            "region",
            "amount",
            "currency",
            "updated_at",
        ]
    )
    count = 0
    for record in rows:
        writer.writerow(
            [
                record.usage_date.isoformat(),
                record.cloud_account.name,
                record.provider_account_id,
                record.project.name if record.project else "",
                record.service,
                record.region,
                str(record.amount),
                record.currency,
                record.updated_at.isoformat(),
            ]
        )
        count += 1
    return _report_result("cost-detail", output, count)


def build_compliance_findings_report(user, *, status=None, severity=None, account_id=None):
    rows = compliance_findings_queryset(user, status=status, severity=severity, account_id=account_id)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["framework", "control", "account", "resource", "resource_type", "severity", "status", "first_seen", "last_seen"])
    count = 0
    for finding in rows:
        writer.writerow([
            finding.control.framework.code,
            finding.control.code,
            finding.cloud_account.name,
            finding.resource.name or finding.resource.provider_resource_id,
            finding.resource.resource_type,
            finding.severity,
            finding.status,
            finding.first_seen.isoformat(),
            finding.last_seen.isoformat(),
        ])
        count += 1
    return _report_result("compliance-findings", output, count)


def build_policy_violations_report(user, *, status=None, severity=None, account_id=None):
    rows = policy_violations_queryset(user, status=status, severity=severity, account_id=account_id)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["policy", "account", "resource", "resource_type", "severity", "status", "first_seen", "last_seen"])
    count = 0
    for violation in rows:
        writer.writerow([
            violation.policy.code,
            violation.cloud_account.name,
            violation.resource.name or violation.resource.provider_resource_id,
            violation.resource.resource_type,
            violation.severity,
            violation.status,
            violation.first_seen.isoformat(),
            violation.last_seen.isoformat(),
        ])
        count += 1
    return _report_result("policy-violations", output, count)


def build_audit_events_report(user, *, action=None, object_type=None):
    rows = audit_events_queryset(user, action=action, object_type=object_type)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["created_at", "actor", "action", "object_type", "object_id", "object_repr"])
    count = 0
    for event in rows:
        writer.writerow([
            event.created_at.isoformat(),
            event.actor.get_username() if event.actor else "",
            event.action,
            event.object_type,
            event.object_id,
            event.object_repr,
        ])
        count += 1
    return _report_result("audit-events", output, count)
