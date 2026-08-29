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

### Slice 5 — Remediation

- Scope remediation request/action reads and direct-ID actions through the target cloud account's organization.
- Reject cross-workspace resource, cloud-account, and recommendation targets before a remediation request is created.
- Ensure a recommendation cannot be paired with a target in a different organization.
- Scope remediation summary counts and status aggregates to the authenticated workspace.
- Keep the allowlisted action catalog shared while all persisted request/event history remains reachable only through tenant-scoped actions.
- Add two-workspace tests for list, retrieve, preview, create, mixed-target validation, and summary isolation.

### Slice 6 — Audit ownership and core relationships

- Stamp new audit records with an organization identifier inferred from the audited object or, when safe, the authenticated user's workspace.
- Preserve explicit audit metadata while preventing object inference from overwriting an explicitly supplied organization identifier.
- Keep existing tenant audit reads non-leaking while ownership metadata becomes durable for newly recorded events.
- Confirm organization-node parents, project nodes, and cloud-account projects cannot cross workspace boundaries through API writes.
- Add two-workspace regression coverage for audit visibility and related-object validation.

### Remaining Sprint 13 slices

- Migrate remaining historical audit/run ownership to explicit schema fields where metadata ownership is insufficient.
- Background evaluation scoping and final exhaustive cross-tenant regression tests.

## Safety gate

Do not configure or activate Stripe, Paddle, AWS Marketplace, or another public payment provider until issue #33 is complete and the two-tenant acceptance tests pass for every paid feature family.
