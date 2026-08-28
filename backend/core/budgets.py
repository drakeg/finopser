import calendar
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .audit import record_audit
from .models import Budget, BudgetAlert, CostRecord

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _scoped_costs(budget, month_start, today):
    queryset = CostRecord.objects.filter(
        usage_date__gte=month_start,
        usage_date__lte=today,
        currency=budget.currency,
    )
    if budget.organization_id:
        queryset = queryset.filter(cloud_account__organization_id=budget.organization_id)
    if budget.node_id:
        queryset = queryset.filter(project__node_id=budget.node_id)
    if budget.project_id:
        queryset = queryset.filter(project_id=budget.project_id)
    if budget.cloud_account_id:
        queryset = queryset.filter(cloud_account_id=budget.cloud_account_id)
    return queryset


def budget_snapshot(budget, today=None):
    today = today or timezone.localdate()
    month_start = today.replace(day=1)
    costs = _scoped_costs(budget, month_start, today)
    actual = costs.aggregate(total=Sum("amount"))["total"] or ZERO
    has_data = costs.exists()
    utilization = (actual / budget.amount * HUNDRED).quantize(Decimal("0.1"))
    remaining = max(budget.amount - actual, ZERO)
    forecast = None
    if has_data:
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        forecast = (actual / Decimal(today.day) * Decimal(days_in_month)).quantize(
            Decimal("0.01")
        )

    if utilization >= HUNDRED:
        level = BudgetAlert.Level.EXCEEDED
    elif utilization >= budget.critical_threshold:
        level = BudgetAlert.Level.CRITICAL
    elif utilization >= budget.warning_threshold:
        level = BudgetAlert.Level.WARNING
    else:
        level = "ok"

    return {
        "period": month_start,
        "actual": actual,
        "remaining": remaining,
        "utilization": utilization,
        "forecast": forecast,
        "currency": budget.currency,
        "level": level,
        "has_data": has_data,
    }


def evaluate_budgets(actor=None, today=None):
    today = today or timezone.localdate()
    snapshots = []
    for budget in Budget.objects.filter(enabled=True).order_by("name", "id"):
        snapshot = budget_snapshot(budget, today)
        period = snapshot["period"]
        active_levels = set()
        if snapshot["level"] == BudgetAlert.Level.WARNING:
            active_levels.add(BudgetAlert.Level.WARNING)
        elif snapshot["level"] == BudgetAlert.Level.CRITICAL:
            active_levels.update({BudgetAlert.Level.WARNING, BudgetAlert.Level.CRITICAL})
        elif snapshot["level"] == BudgetAlert.Level.EXCEEDED:
            active_levels.update(
                {
                    BudgetAlert.Level.WARNING,
                    BudgetAlert.Level.CRITICAL,
                    BudgetAlert.Level.EXCEEDED,
                }
            )

        for level in BudgetAlert.Level.values:
            alert = BudgetAlert.objects.filter(
                budget=budget, period=period, level=level
            ).first()
            if level in active_levels:
                if alert is None:
                    BudgetAlert.objects.create(
                        budget=budget,
                        period=period,
                        level=level,
                        status=BudgetAlert.Status.OPEN,
                        actual_amount=snapshot["actual"],
                        utilization=snapshot["utilization"],
                        first_seen=timezone.now(),
                        last_seen=timezone.now(),
                    )
                else:
                    alert.status = BudgetAlert.Status.OPEN
                    alert.actual_amount = snapshot["actual"]
                    alert.utilization = snapshot["utilization"]
                    alert.last_seen = timezone.now()
                    alert.resolved_at = None
                    alert.save(
                        update_fields=[
                            "status",
                            "actual_amount",
                            "utilization",
                            "last_seen",
                            "resolved_at",
                        ]
                    )
            elif alert and alert.status == BudgetAlert.Status.OPEN:
                alert.status = BudgetAlert.Status.RESOLVED
                alert.resolved_at = timezone.now()
                alert.last_seen = timezone.now()
                alert.save(update_fields=["status", "resolved_at", "last_seen"])
        snapshots.append((budget, snapshot))

    if actor is not None:
        audit_target = Budget.objects.order_by("id").first()
        if audit_target:
            record_audit(
                actor,
                "budget.evaluate",
                audit_target,
                {
                    "budget_count": len(snapshots),
                    "period": today.replace(day=1).isoformat(),
                },
            )
    return snapshots
