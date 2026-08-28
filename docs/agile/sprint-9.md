# Sprint 9 — Budgets & Financial Governance

## Goal

Turn persisted cloud cost evidence into scoped monthly financial guardrails that make budget posture immediately visible without creating AWS Budgets resources or automatically controlling cloud spend.

## Committed scope

- Monthly budget definitions scoped to organization, direct organization node, project, and/or cloud account.
- Amount, currency, warning threshold, critical threshold, enabled state, and audit lifecycle.
- Persisted-cost-only actual, remaining, utilization, and elapsed-month forecast calculations.
- Durable warning, critical, and exceeded alert lifecycle.
- Budget list, alert list, evaluation, and summary APIs.
- FinOps Analyst write/evaluate access alongside Cloud and Platform Administrators; authenticated read access.
- Dashboard and dedicated Budgets UI visibility.
- Tests for persisted-only evaluation, scope/currency isolation, threshold transitions, no-data behavior, validation, and RBAC.
- Architecture documentation for math, evidence semantics, and safety boundaries.

## Readiness gate

Sprint 8 is merged to `main`. Sprint 9 uses the existing `CostRecord`, organization hierarchy, RBAC, audit, API, frontend, Docker, and CI foundations. No additional service, worker, scheduled cloud polling path, frontend chart dependency, CI job, or Docker image is required.

## Locked semantics

- Calendar-month budgets only.
- Actual = matching persisted costs from month start through today.
- Remaining = max(amount - actual, 0).
- Utilization = actual / amount × 100.
- Forecast = actual / elapsed days × calendar days when matching evidence exists; otherwise unknown.
- `0 < warning < critical < 100`; exceeded begins at 100% utilization.
- Currency must match exactly; Sprint 9 performs no FX conversion.
- Configured scope constraints are intersected. Node scope includes projects directly attached to the node.
- Alerts are durable per budget + month + level and can resolve/reopen as persisted evidence changes.

## Non-goals

- AWS Budgets creation/mutation.
- External email/SMS/Slack delivery.
- Rolling, quarterly, or annual budget periods.
- Currency conversion.
- Automatic spend controls, account suspension, SCP/IAM mutation, or remediation.
- Recommendation engine (Sprint 10).
- Automation/remediation (Sprint 11).
- AWS production deployment or paid activation.

## Definition of Done

Existing CI is green; Docker Compose remains cloud-call-free on startup; budget calculations are deterministic and evidence-backed; no budget endpoint calls AWS; threshold lifecycle and RBAC are tested; and the web UI clearly shows current financial posture.
