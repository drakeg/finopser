# Operational Dashboard

Sprint 6 adds `/api/dashboard/`, an authenticated aggregation endpoint built entirely from persisted finopser data.

## Data sources

The dashboard reads existing `CloudAccount`, `CloudResource`, `InventorySync`, `CostRecord`, and `CostSync` records. It does not invoke the cloud-provider registry or make AWS API calls.

The payload contains month-to-date and comparable prior-period spend, top cost dimensions, active/inactive inventory summaries, account validation state, latest inventory/cost sync health, and Immediate Attention items.

## Comparable spend

Month-to-date spend is compared with the same number of calendar days from the prior month when data is available. A percentage is omitted when the prior comparable period is zero.

## Immediate Attention

Sprint 6 operational signals are deterministic views of persisted evidence:

- invalid or unvalidated cloud accounts
- failed or partial latest inventory syncs
- inventory with no complete sync in the last 24 hours
- failed latest cost syncs
- resources retained as inactive
- current-month spend more than 20% above the comparable prior-month period

Signals are ordered high, medium, then low severity. They are not compliance findings, recommendations, budgets, or remediation instructions; those concepts remain assigned to later roadmap Sprints.

## Safety and performance

The dashboard is OBSERVE-only. Docker startup does not call AWS, dashboard rendering does not call AWS, and CI uses persisted test fixtures only. No new frontend dependency, worker, scheduler, CI job, or Docker image build is required by Sprint 6.