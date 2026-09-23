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
