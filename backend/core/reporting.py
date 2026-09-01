import csv
import io
from dataclasses import dataclass

from django.utils import timezone

from .models import CloudResource, CostRecord
from .tenant_scope import scope_queryset

MAX_SYNC_ROWS = 5000


@dataclass(frozen=True)
class ReportDefinition:
    code: str
    name: str
    description: str
    format: str
    target: str


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
}


def report_catalog():
    return [definition.__dict__ for definition in REPORT_CATALOG.values()]


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
