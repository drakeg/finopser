import calendar
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .audit import record_audit
from .budgets import budget_snapshot
from .models import Budget, CloudResource, CostRecord, PolicyViolation
from .recommendation_models import Recommendation, RecommendationRun


def _upsert(source_key, defaults, now):
    recommendation = Recommendation.objects.filter(source_key=source_key).first()
    if recommendation is None:
        return Recommendation.objects.create(
            source_key=source_key,
            first_seen=now,
            last_seen=now,
            **defaults,
        ), True
    for key, value in defaults.items():
        setattr(recommendation, key, value)
    recommendation.last_seen = now
    recommendation.resolved_at = None
    if recommendation.status == Recommendation.Status.RESOLVED:
        recommendation.status = Recommendation.Status.OPEN
    recommendation.save()
    return recommendation, False


def _cost_growth_candidates(today):
    month_start = today.replace(day=1)
    previous_month_end = month_start - timedelta(days=1)
    previous_start = previous_month_end.replace(day=1)
    comparable_days = min(today.day, previous_month_end.day)
    previous_end = previous_start + timedelta(days=comparable_days)
    current = (
        CostRecord.objects.filter(usage_date__gte=month_start, usage_date__lte=today)
        .values("cloud_account", "cloud_account__name", "project", "service", "currency")
        .annotate(total=Sum("amount"))
    )
    previous = {
        (row["cloud_account"], row["service"], row["currency"]): row["total"]
        for row in CostRecord.objects.filter(
            usage_date__gte=previous_start,
            usage_date__lt=previous_end,
        )
        .values("cloud_account", "service", "currency")
        .annotate(total=Sum("amount"))
    }
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    for row in current:
        prior = previous.get(
            (row["cloud_account"], row["service"], row["currency"])
        ) or Decimal("0")
        if prior <= 0:
            continue
        delta = row["total"] - prior
        growth = delta / prior * Decimal("100")
        if growth <= Decimal("20") or delta < Decimal("10"):
            continue
        monthly_excess = (
            delta / Decimal(today.day) * Decimal(days_in_month)
        ).quantize(Decimal("0.01"))
        yield row, prior, growth.quantize(Decimal("0.1")), monthly_excess


def generate_recommendations(actor=None, today=None):
    today = today or timezone.localdate()
    now = timezone.now()
    run = RecommendationRun.objects.create(started_at=now)
    seen = set()
    generated = 0

    for row, prior, growth, monthly_excess in _cost_growth_candidates(today):
        source_key = (
            f"cost-growth:{today:%Y-%m}:{row['cloud_account']}:"
            f"{row['service']}:{row['currency']}"
        )
        seen.add(source_key)
        _, created = _upsert(
            source_key,
            {
                "source_type": "cost_growth",
                "category": Recommendation.Category.COST,
                "priority": (
                    Recommendation.Priority.HIGH
                    if growth >= 50
                    else Recommendation.Priority.MEDIUM
                ),
                "title": f"Review rising {row['service']} spend",
                "detail": (
                    f"Comparable-period spend increased {growth}% for "
                    f"{row['cloud_account__name']}."
                ),
                "action": (
                    "Review the service cost drivers and confirm the increase is "
                    "expected before month end."
                ),
                "estimated_monthly_savings": monthly_excess,
                "evidence": {
                    "current_comparable": str(row["total"]),
                    "previous_comparable": str(prior),
                    "growth_percent": str(growth),
                    "currency": row["currency"],
                    "period": today.strftime("%Y-%m"),
                },
                "cloud_account_id": row["cloud_account"],
                "project_id": row["project"],
                "resource": None,
            },
            now,
        )
        generated += int(created)

    for budget in Budget.objects.filter(enabled=True).order_by("id"):
        snapshot = budget_snapshot(budget, today)
        if snapshot["forecast"] is None or snapshot["forecast"] <= budget.amount:
            continue
        source_key = f"budget-forecast:{today:%Y-%m}:{budget.id}"
        seen.add(source_key)
        overage = snapshot["forecast"] - budget.amount
        ratio = snapshot["forecast"] / budget.amount
        _, created = _upsert(
            source_key,
            {
                "source_type": "budget_forecast",
                "category": Recommendation.Category.COST,
                "priority": (
                    Recommendation.Priority.CRITICAL
                    if ratio >= Decimal("1.20")
                    else Recommendation.Priority.HIGH
                ),
                "title": f"Budget forecast exceeds {budget.name}",
                "detail": (
                    f"Current run rate forecasts {budget.currency} "
                    f"{snapshot['forecast']} against a {budget.amount} budget."
                ),
                "action": (
                    "Review the largest cost drivers in this budget scope and decide "
                    "whether to reduce spend or revise the budget."
                ),
                "estimated_monthly_savings": overage.quantize(Decimal("0.01")),
                "evidence": {
                    "actual": str(snapshot["actual"]),
                    "forecast": str(snapshot["forecast"]),
                    "budget": str(budget.amount),
                    "currency": budget.currency,
                    "utilization": str(snapshot["utilization"]),
                },
                "cloud_account": budget.cloud_account,
                "project": budget.project,
                "resource": None,
            },
            now,
        )
        generated += int(created)

    for resource in CloudResource.objects.filter(is_active=True, tags={}).select_related(
        "cloud_account"
    ):
        source_key = f"untagged-resource:{resource.id}"
        seen.add(source_key)
        _, created = _upsert(
            source_key,
            {
                "source_type": "untagged_resource",
                "category": Recommendation.Category.GOVERNANCE,
                "priority": Recommendation.Priority.LOW,
                "title": (
                    f"Add ownership tags to "
                    f"{resource.name or resource.provider_resource_id}"
                ),
                "detail": (
                    "This active resource has no persisted tags, reducing cost "
                    "allocation and ownership visibility."
                ),
                "action": (
                    "Review the resource and add the organization-standard ownership "
                    "and allocation tags in AWS."
                ),
                "estimated_monthly_savings": None,
                "evidence": {
                    "resource_type": resource.resource_type,
                    "region": resource.region,
                },
                "cloud_account": resource.cloud_account,
                "project": resource.cloud_account.project,
                "resource": resource,
            },
            now,
        )
        generated += int(created)

    violations = PolicyViolation.objects.filter(
        status=PolicyViolation.Status.OPEN
    ).select_related("policy", "resource", "cloud_account")
    for violation in violations:
        source_key = f"policy-violation:{violation.id}"
        seen.add(source_key)
        priority = (
            violation.severity
            if violation.severity in Recommendation.Priority.values
            else Recommendation.Priority.MEDIUM
        )
        _, created = _upsert(
            source_key,
            {
                "source_type": "policy_violation",
                "category": Recommendation.Category.GOVERNANCE,
                "priority": priority,
                "title": violation.policy.name,
                "detail": (
                    f"Open policy violation for "
                    f"{violation.resource.name or violation.resource.provider_resource_id}."
                ),
                "action": (
                    "Review the policy evidence and apply the recommended configuration "
                    "change through the normal cloud change process."
                ),
                "estimated_monthly_savings": None,
                "evidence": {
                    "policy": violation.policy.code,
                    **(violation.evidence or {}),
                },
                "cloud_account": violation.cloud_account,
                "project": violation.cloud_account.project,
                "resource": violation.resource,
            },
            now,
        )
        generated += int(created)

    resolved = 0
    stale = Recommendation.objects.filter(status=Recommendation.Status.OPEN).exclude(
        source_key__in=seen
    )
    for recommendation in stale:
        recommendation.status = Recommendation.Status.RESOLVED
        recommendation.resolved_at = now
        recommendation.last_seen = now
        recommendation.save(update_fields=["status", "resolved_at", "last_seen"])
        resolved += 1

    run.completed_at = timezone.now()
    run.generated_count = generated
    run.resolved_count = resolved
    run.open_count = Recommendation.objects.filter(
        status=Recommendation.Status.OPEN
    ).count()
    run.dismissed_count = Recommendation.objects.filter(
        status=Recommendation.Status.DISMISSED
    ).count()
    run.save()
    if actor is not None:
        record_audit(
            actor,
            "recommendation.generate",
            run,
            {
                "generated": generated,
                "resolved": resolved,
                "open": run.open_count,
                "dismissed": run.dismissed_count,
            },
        )
    return run
