from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .entitlements import user_organization
from .models import CloudAccount, CloudResource, CostRecord, CostSync, InventorySync
from .rbac import GovernancePermission

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
INVENTORY_STALE_AFTER = timedelta(hours=24)


def _decimal_total(queryset) -> Decimal:
    return queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0")


def _previous_month_period(today):
    current_start = today.replace(day=1)
    previous_month_end = current_start - timedelta(days=1)
    previous_start = previous_month_end.replace(day=1)
    comparable_days = min(today.day, previous_month_end.day)
    previous_end = previous_start + timedelta(days=comparable_days)
    return previous_start, previous_end


def _daily_series(queryset):
    return list(
        queryset.values("usage_date")
        .annotate(total=Sum("amount"))
        .order_by("usage_date")
    )


def _attention_item(*, severity, kind, title, detail, target, object_id=None):
    return {
        "severity": severity,
        "kind": kind,
        "title": title,
        "detail": detail,
        "target": target,
        "object_id": object_id,
    }


def _build_attention(accounts, resources, now, mtd, previous_comparable):
    items = []

    for account in accounts.order_by("name"):
        if account.status == CloudAccount.Status.INVALID:
            items.append(
                _attention_item(
                    severity="high",
                    kind="account_validation",
                    title=f"AWS account validation failed: {account.name}",
                    detail=account.last_error or "The most recent account validation failed.",
                    target="Accounts",
                    object_id=account.id,
                )
            )
        elif account.status == CloudAccount.Status.UNVALIDATED:
            items.append(
                _attention_item(
                    severity="medium",
                    kind="account_validation",
                    title=f"AWS account has not been validated: {account.name}",
                    detail="Validate the configured AssumeRole trust before relying on account data.",
                    target="Accounts",
                    object_id=account.id,
                )
            )

        latest_inventory = account.inventory_syncs.order_by("-started_at").first()
        if latest_inventory:
            if latest_inventory.status == InventorySync.Status.FAILED:
                items.append(
                    _attention_item(
                        severity="high",
                        kind="inventory_sync",
                        title=f"Inventory sync failed: {account.name}",
                        detail="The latest inventory sync failed.",
                        target="Resources",
                        object_id=latest_inventory.id,
                    )
                )
            elif latest_inventory.status == InventorySync.Status.PARTIAL:
                items.append(
                    _attention_item(
                        severity="medium",
                        kind="inventory_sync",
                        title=f"Inventory sync partially completed: {account.name}",
                        detail=f"{len(latest_inventory.errors)} collector error(s) were recorded.",
                        target="Resources",
                        object_id=latest_inventory.id,
                    )
                )

        latest_success = (
            account.inventory_syncs.filter(status=InventorySync.Status.SUCCESS)
            .order_by("-completed_at")
            .first()
        )
        if (
            latest_success
            and latest_success.completed_at
            and now - latest_success.completed_at > INVENTORY_STALE_AFTER
        ):
            items.append(
                _attention_item(
                    severity="medium",
                    kind="inventory_stale",
                    title=f"Inventory may be stale: {account.name}",
                    detail="The last complete inventory sync is more than 24 hours old.",
                    target="Resources",
                    object_id=latest_success.id,
                )
            )

        latest_cost = account.cost_syncs.order_by("-started_at").first()
        if latest_cost and latest_cost.status == CostSync.Status.FAILED:
            items.append(
                _attention_item(
                    severity="high",
                    kind="cost_sync",
                    title=f"Cost sync failed: {account.name}",
                    detail="The latest cost sync failed.",
                    target="Costs",
                    object_id=latest_cost.id,
                )
            )

    inactive_count = resources.filter(is_active=False).count()
    if inactive_count:
        items.append(
            _attention_item(
                severity="low",
                kind="inactive_resources",
                title=f"{inactive_count} previously discovered resource(s) are inactive",
                detail="Review inventory history for resources no longer seen in a complete sync.",
                target="Resources",
            )
        )

    if previous_comparable > 0 and mtd > previous_comparable * Decimal("1.20"):
        increase = (
            (mtd - previous_comparable) / previous_comparable * Decimal("100")
        ).quantize(Decimal("0.1"))
        items.append(
            _attention_item(
                severity="medium",
                kind="cost_increase",
                title="Month-to-date spend is materially higher",
                detail=(
                    f"Comparable spend is up {increase}% versus the same number of days last month."
                ),
                target="Costs",
            )
        )

    return sorted(
        items,
        key=lambda item: (SEVERITY_RANK[item["severity"]], item["title"]),
    )


@api_view(["GET"])
@permission_classes([GovernancePermission])
def operational_dashboard(request):
    today = timezone.localdate()
    now = timezone.now()
    month_start = today.replace(day=1)
    previous_start, previous_end = _previous_month_period(today)

    accounts = CloudAccount.objects.all()
    resources_queryset = CloudResource.objects.all()
    costs = CostRecord.objects.select_related("cloud_account", "project")
    inventory_syncs = InventorySync.objects.select_related("cloud_account")
    cost_syncs = CostSync.objects.select_related("cloud_account")
    if not request.user.is_superuser:
        organization = user_organization(request.user)
        organization_id = organization.id if organization else -1
        accounts = accounts.filter(organization_id=organization_id)
        resources_queryset = resources_queryset.filter(
            cloud_account__organization_id=organization_id
        )
        costs = costs.filter(cloud_account__organization_id=organization_id)
        inventory_syncs = inventory_syncs.filter(cloud_account__organization_id=organization_id)
        cost_syncs = cost_syncs.filter(cloud_account__organization_id=organization_id)

    mtd_costs = costs.filter(usage_date__gte=month_start, usage_date__lte=today)
    previous_costs = costs.filter(usage_date__gte=previous_start, usage_date__lt=previous_end)
    mtd = _decimal_total(mtd_costs)
    previous_comparable = _decimal_total(previous_costs)
    change_percent = None
    if previous_comparable:
        change_percent = (
            (mtd - previous_comparable) / previous_comparable * Decimal("100")
        ).quantize(Decimal("0.1"))

    active_resources = resources_queryset.filter(is_active=True)
    resources = {
        "total": resources_queryset.count(),
        "active": active_resources.count(),
        "inactive": resources_queryset.filter(is_active=False).count(),
        "by_type": list(
            active_resources.values("resource_type")
            .annotate(count=Count("id"))
            .order_by("-count", "resource_type")[:8]
        ),
        "by_account": list(
            active_resources.values("cloud_account", "cloud_account__name")
            .annotate(count=Count("id"))
            .order_by("-count", "cloud_account__name")[:8]
        ),
        "by_region": list(
            active_resources.values("region")
            .annotate(count=Count("id"))
            .order_by("-count", "region")[:8]
        ),
    }

    top_costs = {
        "service": list(
            mtd_costs.values("service")
            .annotate(total=Sum("amount"))
            .order_by("-total", "service")[:8]
        ),
        "account": list(
            mtd_costs.values("cloud_account", "cloud_account__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:8]
        ),
        "project": list(
            mtd_costs.values("project", "project__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:8]
        ),
        "region": list(
            mtd_costs.values("region")
            .annotate(total=Sum("amount"))
            .order_by("-total", "region")[:8]
        ),
    }

    account_status = list(
        accounts.values("status").annotate(count=Count("id")).order_by("status")
    )
    latest_inventory = (
        inventory_syncs.order_by("cloud_account_id", "-started_at").distinct("cloud_account_id")
    )
    latest_cost = cost_syncs.order_by("cloud_account_id", "-started_at").distinct(
        "cloud_account_id"
    )

    return Response(
        {
            "generated_at": now,
            "spend": {
                "mtd": mtd,
                "previous_comparable": previous_comparable,
                "change_percent": change_percent,
                "currency": "USD",
                "daily": _daily_series(mtd_costs),
                "previous_daily": _daily_series(previous_costs),
            },
            "resources": resources,
            "top_costs": top_costs,
            "accounts": {
                "total": accounts.count(),
                "by_status": account_status,
            },
            "sync_health": {
                "inventory": [
                    {
                        "account_id": sync.cloud_account_id,
                        "account_name": sync.cloud_account.name,
                        "status": sync.status,
                        "started_at": sync.started_at,
                        "completed_at": sync.completed_at,
                    }
                    for sync in latest_inventory
                ],
                "costs": [
                    {
                        "account_id": sync.cloud_account_id,
                        "account_name": sync.cloud_account.name,
                        "status": sync.status,
                        "started_at": sync.started_at,
                        "completed_at": sync.completed_at,
                    }
                    for sync in latest_cost
                ],
            },
            "attention": _build_attention(
                accounts,
                resources_queryset,
                now,
                mtd,
                previous_comparable,
            ),
        }
    )
