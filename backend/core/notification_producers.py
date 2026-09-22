from .notification_dispatch import dispatch_notification_event


def budget_threshold_source_id(budget, snapshot) -> str:
    return f"budget:{budget.id}:{snapshot['period'].isoformat()}:{snapshot['level']}"


def budget_threshold_payload(budget, snapshot) -> dict:
    return {
        "budget_id": budget.id,
        "budget_name": budget.name,
        "period": snapshot["period"].isoformat(),
        "level": snapshot["level"],
        "utilization": str(snapshot["utilization"]),
        "actual": str(snapshot["actual"]),
        "amount": str(budget.amount),
        "currency": snapshot["currency"],
    }


def dispatch_budget_threshold(
    budget,
    snapshot,
    *,
    signing_secret_for,
    transport,
    actor=None,
):
    if not budget.organization_id or snapshot["level"] == "ok":
        return []
    return dispatch_notification_event(
        budget.organization,
        "cost.threshold",
        budget_threshold_source_id(budget, snapshot),
        budget_threshold_payload(budget, snapshot),
        signing_secret_for,
        transport,
        actor=actor,
    )
