import csv
import io
from dataclasses import asdict, dataclass

from django.utils import timezone

from .automation_models import RemediationAction
from .entitlements import has_feature
from .recommendation_models import Recommendation
from .reporting import MAX_SYNC_ROWS
from .tenant_scope import scope_queryset


@dataclass(frozen=True)
class ActionReportDefinition:
    code: str
    name: str
    description: str
    format: str
    target: str
    feature: str


ACTION_REPORT_CATALOG = {
    "recommendations": ActionReportDefinition(
        code="recommendations",
        name="Recommendations",
        description="Persisted recommendations with priority, category, target, lifecycle state, and derived savings.",
        format="csv",
        target="Recommendations",
        feature="recommendations",
    ),
    "remediation-history": ActionReportDefinition(
        code="remediation-history",
        name="Remediation history",
        description="Persisted remediation requests and lifecycle outcomes without parameters or provider-result payloads.",
        format="csv",
        target="Automation",
        feature="remediation_simulation",
    ),
}


def action_report_catalog(user):
    return [
        asdict(definition)
        for definition in ACTION_REPORT_CATALOG.values()
        if has_feature(user, definition.feature)
    ]


def action_report_allowed(user, code):
    return has_feature(user, ACTION_REPORT_CATALOG[code].feature)


def recommendations_queryset(user, *, status=None, priority=None, category=None, account_id=None):
    queryset = scope_queryset(
        Recommendation.objects.select_related("cloud_account", "project", "resource").order_by(
            "status", "priority", "category", "title", "id"
        ),
        user,
    )
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if category:
        queryset = queryset.filter(category=category)
    if account_id:
        queryset = queryset.filter(cloud_account_id=account_id)
    return queryset[:MAX_SYNC_ROWS]


def remediation_history_queryset(user, *, status=None, simulation=None, account_id=None):
    queryset = scope_queryset(
        RemediationAction.objects.select_related(
            "cloud_account", "resource", "requested_by", "approved_by", "executed_by"
        ).order_by("-requested_at", "id"),
        user,
        lookup="cloud_account__organization_id",
    )
    if status:
        queryset = queryset.filter(status=status)
    if simulation is not None:
        queryset = queryset.filter(simulation=simulation)
    if account_id:
        queryset = queryset.filter(cloud_account_id=account_id)
    return queryset[:MAX_SYNC_ROWS]


def _result(code, output, count):
    return {
        "generated_at": timezone.now(),
        "report": ACTION_REPORT_CATALOG[code],
        "row_count": count,
        "truncated": count >= MAX_SYNC_ROWS,
        "content": output.getvalue(),
    }


def build_recommendations_report(user, *, status=None, priority=None, category=None, account_id=None):
    rows = recommendations_queryset(
        user,
        status=status,
        priority=priority,
        category=category,
        account_id=account_id,
    )
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "status", "priority", "category", "title", "recommended_action",
        "estimated_monthly_savings", "account", "project", "resource",
        "first_seen", "last_seen",
    ])
    count = 0
    for recommendation in rows:
        writer.writerow([
            recommendation.status,
            recommendation.priority,
            recommendation.category,
            recommendation.title,
            recommendation.action,
            "" if recommendation.estimated_monthly_savings is None else str(recommendation.estimated_monthly_savings),
            recommendation.cloud_account.name if recommendation.cloud_account else "",
            recommendation.project.name if recommendation.project else "",
            (recommendation.resource.name or recommendation.resource.provider_resource_id) if recommendation.resource else "",
            recommendation.first_seen.isoformat(),
            recommendation.last_seen.isoformat(),
        ])
        count += 1
    return _result("recommendations", output, count)


def build_remediation_history_report(user, *, status=None, simulation=None, account_id=None):
    rows = remediation_history_queryset(user, status=status, simulation=simulation, account_id=account_id)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "status", "action", "account", "resource", "resource_type", "simulation",
        "requested_by", "requested_at", "approved_by", "approved_at",
        "executed_by", "executed_at", "error",
    ])
    count = 0
    for action in rows:
        writer.writerow([
            action.status,
            action.action_key,
            action.cloud_account.name,
            action.resource.name or action.resource.provider_resource_id,
            action.resource.resource_type,
            "true" if action.simulation else "false",
            action.requested_by.get_username() if action.requested_by else "",
            action.requested_at.isoformat(),
            action.approved_by.get_username() if action.approved_by else "",
            action.approved_at.isoformat() if action.approved_at else "",
            action.executed_by.get_username() if action.executed_by else "",
            action.executed_at.isoformat() if action.executed_at else "",
            action.error,
        ])
        count += 1
    return _result("remediation-history", output, count)
