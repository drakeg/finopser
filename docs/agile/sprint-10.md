# Sprint 10 — Recommendations

## Goal
Turn Finopser's persisted inventory, cost, budget, and policy evidence into prioritized, explainable recommendations without mutating cloud resources.

## Recommendation sources
Sprint 10 initially generates recommendations from four persisted-data conditions:

1. **Material service cost growth** — current comparable-period spend for an account/service is more than 20% and at least $10 above the prior comparable period.
2. **Forecast budget overrun** — the Sprint 9 elapsed-day run-rate forecast exceeds an enabled monthly budget.
3. **Untagged active resources** — an active normalized cloud resource has no persisted tags.
4. **Open policy violations** — an actionable Sprint 8 policy violation remains open.

Compliance findings are not separately duplicated when the same evidence is already represented by a policy violation.

## Provenance and lifecycle
Every recommendation has a stable `source_key`, category, priority, evidence, target/action text, optional account/project/resource links, and first/last observed timestamps. Current conditions remain open. Conditions that disappear resolve automatically. A user-dismissed recommendation remains dismissed when generation sees the same source again. Periodic sources such as cost growth and budget forecasts include the calendar month in their source identity, so a genuinely new period can create a new recommendation.

## Estimated monthly savings
Savings are optional. Finopser does not invent a dollar value for governance or operational recommendations. For material cost-growth recommendations, estimated monthly savings is the current comparable-period excess versus the prior comparable period, normalized to the number of calendar days in the current month:

`(current comparable spend - previous comparable spend) / elapsed days * days in month`

For a forecast budget overrun, estimated monthly savings is the forecast amount above the configured budget. It represents the reduction required to land at budget, not a guaranteed realized saving.

## Safety boundary
Recommendation generation reads persisted database records only. It makes no boto3, AWS, Terraform, IAM, SCP, resource mutation, or external notification call. A recommendation is advice; applying it remains an explicit human/cloud-change workflow until a later authorized automation design.

## API
- `GET /api/recommendations/`
- `GET /api/recommendations/summary/`
- `POST /api/recommendations/generate/`
- `POST /api/recommendations/<id>/dismiss/`
- `POST /api/recommendations/<id>/reopen/`
- `GET /api/recommendation-runs/`

Read access follows authenticated governance visibility. Generation/dismiss/reopen is limited to Platform Administrator, Cloud Administrator, FinOps Analyst, and Security / Compliance Engineer roles. Important actions are audited.

## Non-goals
- AWS Compute Optimizer or Trusted Advisor integration.
- Rightsizing based on CPU/memory telemetry not currently persisted.
- Automated remediation, stopping, deleting, resizing, or reconfiguring resources.
- IAM/SCP mutation or Terraform execution.
- External notifications or paid service activation.
- Scheduled provider polling.

## Acceptance
Recommendation generation must be deterministic, evidence-backed, cloud-call-free, lifecycle-aware, dismissible, auditable, visible in the web UI, and pass the existing backend/frontend/Docker CI path without adding a new CI job, duplicate image build, or heavy frontend dependency.
