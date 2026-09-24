# Product Acceptance Matrix

This matrix is a living release-readiness check. A completed sprint means its accepted slice shipped at that time; it does not replace checking the current product surface for regressions.

| Epic | Current evidence | Product surface | Audit status |
|---|---|---|---|
| E001 Foundation | health/readiness, Docker Compose, CI quality gates | local stack + CI | Verified |
| E002 Authentication & RBAC | session auth and server-side role checks | sign-in + protected APIs | Verified |
| E003 Organizational hierarchy | organizations, nodes, projects and scoped APIs | Organization workspace | Verified |
| E004–E007 AWS/account/inventory/cost | provider/account models, inventory and cost APIs | Accounts, Resources, Costs | Verified current self-hosted scope |
| E008 Dashboard | operational summaries and attention signals | Dashboard | Verified |
| E009–E010 Compliance/policies | findings, controls, policies and violations | Compliance, Policies | Verified |
| E011 Recommendations | recommendation lifecycle and evidence | Recommendations | Verified |
| E012 Remediation | approval-gated execution boundary | Automation | Verified safe/default-disabled scope |
| E013 Budgets | budgets, threshold evidence and notifications producer | Budgets | Verified |
| E014 Notifications | channels, sanitized delivery history, injected transport | Administration/integrations | Verified safe/default-no-network scope |
| E015 Reporting/export | catalog, CSV exports, schedule intent, explicit generation history | Reports | Verified current scope in Sprint 30 |
| E016 Audit/evidence | tenant-scoped audit events/integrity evidence | Administration/reports | Verified |
| E017 Enterprise identity | discovery + local OIDC flow boundary, local password fallback | Sign-in | Verified safe/provider-neutral scope |
| E018 AWS account vending | request/approve/reject backend, plan/execution boundary | Administration | **Gap fixed in Sprint 31:** Reject action was missing from UI |
| E022 Public API/CLI/integrations | versioned read-only API, service principals/tokens, webhook boundaries | API/CLI + Administration | Verified current read-only scope |

## Audit rules

- Backend authorization remains authoritative; UI presence is not treated as security enforcement.
- Provider-neutral/default-disabled boundaries are considered complete only for the explicitly documented local scope, not as claims of live cloud execution.
- A regression found here becomes a Sprint issue and receives focused acceptance coverage rather than being documented away.
- Azure, GCP, OCI, live AWS account creation, hosted SSO, hosted scheduling, and automatic external delivery remain outside the currently authorized scope.
