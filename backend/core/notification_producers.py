from .notification_dispatch import dispatch_notification_event
from .reporting import REPORT_CATALOG


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


def governance_finding_source_id(finding) -> str:
    return f"compliance-finding:{finding.id}"


def governance_finding_payload(finding) -> dict:
    return {
        "finding_id": finding.id,
        "control_code": finding.control.code,
        "control_title": finding.control.title,
        "severity": finding.severity,
        "status": finding.status,
        "resource_id": finding.resource.provider_resource_id,
        "resource_type": finding.resource.resource_type,
        "region": finding.resource.region,
    }


def dispatch_governance_finding(
    finding,
    *,
    signing_secret_for,
    transport,
    actor=None,
):
    if finding.status != finding.Status.OPEN:
        return []
    organization = finding.cloud_account.organization
    return dispatch_notification_event(
        organization,
        "governance.finding",
        governance_finding_source_id(finding),
        governance_finding_payload(finding),
        signing_secret_for,
        transport,
        actor=actor,
    )


def report_ready_payload(report_result) -> dict:
    definition = report_result["report"]
    return {
        "report_code": definition.code,
        "report_name": definition.name,
        "generated_at": report_result["generated_at"].isoformat(),
        "row_count": report_result["row_count"],
        "truncated": report_result["truncated"],
    }


def dispatch_report_ready(
    organization,
    report_result,
    source_id,
    *,
    signing_secret_for,
    transport,
    actor=None,
):
    source_id = str(source_id).strip()
    if not source_id:
        raise ValueError("Report source id is required")
    definition = report_result.get("report")
    if definition is None or definition.code not in REPORT_CATALOG:
        raise ValueError("Unknown report definition")
    return dispatch_notification_event(
        organization,
        "report.ready",
        source_id,
        report_ready_payload(report_result),
        signing_secret_for,
        transport,
        actor=actor,
    )


def recommendation_source_id(recommendation) -> str:
    return f"recommendation:{recommendation.organization_id}:{recommendation.source_key}"


def recommendation_payload(recommendation) -> dict:
    return {
        "recommendation_id": recommendation.id,
        "source_type": recommendation.source_type,
        "category": recommendation.category,
        "priority": recommendation.priority,
        "status": recommendation.status,
        "title": recommendation.title,
        "estimated_monthly_savings": (
            str(recommendation.estimated_monthly_savings)
            if recommendation.estimated_monthly_savings is not None
            else None
        ),
        "account_id": recommendation.cloud_account_id,
        "project_id": recommendation.project_id,
        "resource_id": recommendation.resource_id,
    }


def dispatch_recommendation_open(
    recommendation,
    *,
    signing_secret_for,
    transport,
    actor=None,
):
    if not recommendation.organization_id or recommendation.status != recommendation.Status.OPEN:
        return []
    return dispatch_notification_event(
        recommendation.organization,
        "recommendation.open",
        recommendation_source_id(recommendation),
        recommendation_payload(recommendation),
        signing_secret_for,
        transport,
        actor=actor,
    )


def remediation_event_type(action) -> str | None:
    if action.status == action.Status.PREVIEWED:
        return "remediation.approval_required"
    if action.status in {
        action.Status.SUCCEEDED,
        action.Status.FAILED,
        action.Status.STALE,
        action.Status.REJECTED,
    }:
        return "remediation.completed"
    return None


def remediation_source_id(action) -> str:
    return f"remediation:{action.id}:{action.status}"


def remediation_payload(action) -> dict:
    return {
        "remediation_id": action.id,
        "action_key": action.action_key,
        "status": action.status,
        "simulation": action.simulation,
        "account_id": action.cloud_account_id,
        "resource_id": action.resource_id,
        "resource_type": action.resource.resource_type,
        "recommendation_id": action.recommendation_id,
    }


def dispatch_remediation_lifecycle(
    action,
    *,
    signing_secret_for,
    transport,
    actor=None,
):
    event_type = remediation_event_type(action)
    if event_type is None or not action.cloud_account.organization_id:
        return []
    return dispatch_notification_event(
        action.cloud_account.organization,
        event_type,
        remediation_source_id(action),
        remediation_payload(action),
        signing_secret_for,
        transport,
        actor=actor,
    )



def report_generation_notification_result(generation):
    definition = REPORT_CATALOG.get(generation.report_code)
    if definition is None:
        raise ValueError("Unknown report definition")
    return {
        "report": definition,
        "generated_at": generation.generated_at,
        "row_count": generation.row_count,
        "truncated": generation.truncated,
    }


def dispatch_report_generation_ready(
    generation,
    *,
    signing_secret_for,
    transport,
    actor=None,
):
    if generation.status != generation.Status.SUCCEEDED:
        return []
    return dispatch_report_ready(
        generation.organization,
        report_generation_notification_result(generation),
        f"report-generation:{generation.id}",
        signing_secret_for=signing_secret_for,
        transport=transport,
        actor=actor,
    )
