# Sprint 13 — Paid-feature tenant isolation

## Goal

Harden paid governance capabilities for self-service workspaces before any public billing provider is enabled. Issue #33 remains the acceptance gate for production multi-tenant SaaS.

## Delivery strategy

Tenant isolation is being landed in reviewable slices so each feature family has explicit cross-tenant tests instead of one broad, difficult-to-audit change.

### Slice 1 — Budgets

- Scope budget list/retrieve/update/delete to the authenticated workspace.
- Force new self-service budgets into the authenticated workspace.
- Reject organization, node, project, and cloud-account references outside that workspace.
- Scope budget alerts, summaries, aggregates, and evaluation to the workspace.
- Preserve deliberate legacy/global and superuser behavior.
- Add two-workspace tests proving list, retrieve, summary, and write isolation.

### Remaining Sprint 13 slices

- Compliance findings, exceptions, evaluation, summaries, and run history.
- Governance policies, violations, evaluation, summaries, and run history.
- Recommendations, generation, actions, summaries, and run history.
- Remediation requests, events, target validation, and summaries.
- Organization ownership for historical run/audit records where schema ownership is currently ambiguous.
- Background evaluation scoping and exhaustive cross-tenant regression tests.

## Safety gate

Do not configure or activate Stripe, Paddle, AWS Marketplace, or another public payment provider until issue #33 is complete and the two-tenant acceptance tests pass for every paid feature family.
