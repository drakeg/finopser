# Budgets and Financial Governance

Sprint 9 adds evidence-backed monthly budget governance without creating or mutating AWS Budgets resources.

## Data source and safety boundary

Budget calculations use only persisted `CostRecord` rows already synchronized into Finopser. Reading a budget, loading the dashboard, or evaluating thresholds never calls AWS. Docker Compose startup remains cloud-call-free. Sprint 9 does not suspend accounts, modify IAM/SCPs, deliver notifications, or remediate spend.

## Monthly math

For the current calendar month:

- **Actual** is the sum of matching `CostRecord.amount` values from the first day of the month through today.
- **Utilization** is `actual / budget amount * 100`.
- **Remaining** is `max(budget amount - actual, 0)`.
- **Forecast** is `actual / elapsed calendar days * total calendar days` when at least one matching cost record exists.
- With no matching evidence, actual remains zero and forecast is explicitly unknown rather than guessed.

Sprint 9 does not perform currency conversion. Each budget evaluates only cost records whose currency exactly matches the budget currency.

## Scope

A budget can constrain organization, organization node, project, and cloud account. Configured constraints are intersected. Node scope includes projects directly attached to that node in Sprint 9; recursive descendant-node budget inheritance is intentionally deferred.

## Thresholds and alerts

Budgets require `0 < warning < critical < 100`. The current state is:

- `ok` below warning
- `warning` at or above warning
- `critical` at or above critical
- `exceeded` at or above 100%

`BudgetAlert` records are durable by budget, month, and threshold level. A critical state keeps warning and critical alerts open; exceeded keeps warning, critical, and exceeded alerts open. Alerts resolve when utilization falls below their threshold and reopen if the threshold is crossed again.

These records are internal governance signals only. Sprint 9 does not send email, SMS, Slack, or other external notifications.

## API

- `GET/POST /api/budgets/`
- `GET /api/budget-alerts/`
- `POST /api/budgets/evaluate/`
- `GET /api/budgets/summary/`

Authenticated users can read budget data. Platform Administrators, Cloud Administrators, and FinOps Analysts can create/change budgets and run evaluation. Budget mutations and evaluation are audited.

## Deferred work

Rolling, quarterly, and annual budgets; FX conversion; external notification delivery; AWS Budgets integration; automatic spend controls; recommendations; and remediation are outside Sprint 9.
