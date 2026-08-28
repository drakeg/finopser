# Sprint 13 — Policy tenant isolation slice

This slice advances blocker #33 by applying organization boundaries to governance-policy execution and reporting.

## Scope

- Self-service users see built-in policies plus policies owned by their organization.
- Tenant-created policies are forced into the authenticated organization.
- Related organization, node, project, and cloud-account references are validated against the current workspace.
- Policy evaluation only scans resources in the authenticated organization.
- Policy violations, summary aggregates, and policy run history are organization-scoped.
- Built-in policy definitions remain global and cannot be deleted from a tenant workspace.
- Legacy installations without an organization membership and Django superusers preserve existing global behavior.

## Verification

Two-workspace API tests prove that tenant A cannot list tenant B's custom policies, create a policy targeting tenant B, evaluate tenant B's resources, infer tenant B's violation counts, or read tenant B's policy-run history.

## Remaining Sprint 13 work

Issue #33 remains open. Recommendation generation/history, remediation requests/events/summary, audit-history ownership, and remaining cross-tenant relationship validation still require the same isolation standard before paid billing can be enabled.
