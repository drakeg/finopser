# Sprint 6 — Dashboard / Operational Intelligence

## Sprint Goal

Turn the resource-inventory and FinOps data delivered in Sprints 4–5 into a useful operational dashboard that answers: **What needs attention right now?**

Sprint 6 remains OBSERVE-only. It aggregates already persisted application data and must not introduce automatic AWS calls, resource mutation, remediation, paid-service activation, or recurring spend.

## Scope

- authenticated operational-dashboard API aggregating persisted inventory, cost, cloud-account, and sync-health data
- month-to-date spend and prior-period comparison using existing normalized cost records
- highest-cost services, accounts, projects, and regions
- active/inactive resource counts and resource-type/account/region breakdowns
- cloud-account validation status and recent inventory/cost sync health
- Immediate Attention feed based on deterministic operational conditions available today
- prioritization/severity metadata for attention items without pretending these are formal compliance findings or recommendations
- lightweight dashboard visualizations using the existing frontend stack; no heavyweight chart dependency required
- useful empty/loading/error states
- tests for aggregation, authorization, ordering, and empty-data behavior
- dashboard documentation and Sprint artifacts
- preserve existing API contracts
- keep CI/Docker optimized; no additional CI job or duplicate image build

## Immediate Attention Conditions

Sprint 6 may surface only evidence-backed conditions already represented by persisted data, such as:

1. AWS account validation failed or has never succeeded.
2. Latest inventory sync failed or completed partially.
3. Latest cost sync failed.
4. Inventory is stale based on the most recent successful sync timestamp.
5. Previously discovered resources are now inactive.
6. Material cost increase versus the comparable prior period when enough data exists.

These are operational signals, not Compliance findings (Sprint 7) or Recommendations (Sprint 10).

## Acceptance Criteria

1. An authenticated user can retrieve one operational-dashboard payload without triggering an AWS API call.
2. Dashboard data is computed from persisted FinOps, inventory, cloud-account, and sync-history records.
3. MTD spend and prior-period comparison are available when data exists and degrade cleanly when it does not.
4. Top cost dimensions are available for service, account, project, and region.
5. Resource totals and breakdowns distinguish active and inactive resources.
6. Account-validation and latest sync-health information is visible.
7. Immediate Attention items are deterministic, evidence-backed, ordered by severity/priority, and link to the relevant application area where practical.
8. Empty installations render a useful dashboard rather than failing.
9. Dashboard APIs enforce the existing authenticated/RBAC boundary.
10. Tests run without AWS credentials or network access.
11. Docker startup performs no cloud calls.
12. Existing backend/frontend/Docker CI remains green without adding unnecessary jobs or redundant builds.

## Explicit Non-Goals

- no compliance framework/control/finding model
- no policies or guardrails
- no budgets or financial enforcement
- no recommendation engine
- no automated remediation
- no scheduled AWS polling
- no live AWS calls from the dashboard
- no AWS production deployment
- no paid service activation

## Definition of Done

The repository Definition of Done applies. Sprint 6 is complete only after implementation, automated tests, documentation, CI, review, and merge to `main`.