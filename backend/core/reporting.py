import csv
import io
from dataclasses import dataclass

from django.utils import timezone

from .models import CloudResource
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
    return {
        "generated_at": timezone.now(),
        "report": REPORT_CATALOG["resource-inventory"],
        "row_count": count,
        "truncated": count >= MAX_SYNC_ROWS,
        "content": output.getvalue(),
    }
