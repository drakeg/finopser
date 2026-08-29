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

### Slice 2 — Compliance

- Scope findings, exceptions, evaluation, summaries, aggregates, and run history.
- Evaluate only resources in the authenticated self-service workspace.
- Reject exception targets outside the workspace.
- Keep shared framework/control definitions global.
- Add two-workspace regression coverage for reads, evaluation, aggregates, history, and writes.

### Slice 3 — Governance policies

- Scope custom policies, violations, evaluation, summaries, aggregates, and run history.
- Keep built-in policies globally visible while tenant-created policies remain workspace-owned.
- Force self-service policy creation into the current workspace and validate related scope objects.
- Evaluate only resources in the authenticated workspace.
- Add two-workspace regression coverage for reads, writes, evaluation, aggregates, and history.

### Slice 4 — Recommendations

- Add explicit organization ownership to recommendations and generation runs.
- Change recommendation source identity from globally unique to organization + source key uniqueness.
- Backfill existing recommendation ownership from account, project, or resource relationships where it can be inferred safely.
- Scope cost growth, budget, untagged-resource, and policy-violation generation inputs to the authenticated workspace.
- Scope stale recommendation resolution, run counts, reads, summaries, actions, and run history.
- Add two-workspace tests proving generation cannot create, expose, mutate, aggregate, or resolve another workspace's recommendations.

### Remaining Sprint 13 slices

- Remediation requests, events, target validation, and summaries.
- Organization ownership for remaining historical run/audit records where schema ownership is ambiguous.
- Core relationship validation for organization/node/project/account references.
- Background evaluation scoping and final exhaustive cross-tenant regression tests.

## Safety gate

Do not configure or activate Stripe, Paddle, AWS Marketplace, or another public payment provider until issue #33 is complete and the two-tenant acceptance tests pass for every paid feature family.
