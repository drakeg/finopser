# Product Backlog

## Prioritization

- **P0** — required for the initial usable platform foundation.
- **P1** — high-value capability after the foundation is stable.
- **P2** — important enterprise/integration capability.
- **P3** — future expansion.

## Epics

| Epic | Name | Priority | Outcome |
|---|---|---:|---|
| E001 | Application Foundation | P0 | Deployable application platform with API, UI, data, jobs, health, logging, and CI. |
| E002 | Authentication & RBAC | P0 | Server-side authentication and deny-by-default authorization. |
| E003 | Organizational Hierarchy | P0 | Organizations, recursive organizational nodes, projects, ownership, and inheritance scopes. |
| E004 | AWS Provider Integration | P0 | Provider abstraction plus AWS implementation using STS AssumeRole. |
| E005 | Cloud Account Management | P0 | Register, validate, discover, and manage cloud accounts. |
| E006 | Resource Inventory | P0 | Normalize and browse provider resources across accounts and regions. |
| E007 | FinOps & Cost Management | P0 | Ingest and analyze cloud costs by account, project, service, region, tags, and time. |
| E008 | Dashboard & Visualization | P0 | Operational dashboard focused on immediate attention and actionable risk/cost signals. |
| E009 | Compliance Management | P1 | Frameworks, controls, checks, findings, lifecycle, evidence, and exceptions. |
| E010 | Policies & Guardrails | P1 | Reusable policies assigned by scope with inheritance and exceptions. |
| E011 | Recommendations | P1 | Evidence-backed cost, security, and governance recommendations. |
| E012 | Remediation & Automation | P1 | Controlled jobs and remediation under Observe/Recommend/Enforce rules. |
| E013 | Budgets & Financial Governance | P1 | Budgets, thresholds, allocation, notifications, and later enforcement. |
| E014 | Notifications | P1 | In-app and configurable external notifications. |
| E015 | Reporting & Export | P1 | Interactive reporting and exportable evidence/data. |
| E016 | Audit & Evidence | P0 | Immutable application audit events for privileged and governance-relevant changes. |
| E017 | Enterprise Identity | P2 | OIDC/SAML/SSO and enterprise identity lifecycle. |
| E018 | AWS Account Vending | P2 | Controlled AWS account provisioning and baseline application. |
| E019 | Azure Provider | P3 | Azure provider implementation behind the shared provider interfaces. |
| E020 | GCP Provider | P3 | GCP provider implementation behind the shared provider interfaces. |
| E021 | OCI Provider | P3 | OCI provider implementation behind the shared provider interfaces. |
| E022 | Public API / CLI / Integrations | P2 | Stable external APIs, CLI, and automation integrations. |

## Initial Sprint Roadmap

The roadmap is directional and is re-planned after every Sprint.

1. Sprint 0 — Product & Architecture Foundation
2. Sprint 1 — Application Foundation
3. Sprint 2 — Organization + RBAC
4. Sprint 3 — AWS Account Onboarding
5. Sprint 4 — Resource Inventory
6. Sprint 5 — FinOps MVP
7. Sprint 6 — Dashboard / Operational Intelligence
8. Sprint 7 — Compliance MVP
9. Sprint 8 — Policies & Guardrails
10. Sprint 9 — Budgets & Financial Governance
11. Sprint 10 — Recommendations
12. Sprint 11 — Automation / Remediation

## Sprint 1 Candidate Stories

- **FIN-001** Repository/application structure and development conventions.
- **FIN-002** Backend application with health endpoints and configuration framework.
- **FIN-003** PostgreSQL integration and migration foundation.
- **FIN-004** Redis integration.
- **FIN-005** Background worker and scheduler infrastructure.
- **FIN-006** Frontend application shell and navigation.
- **FIN-007** Docker Compose local deployment.
- **FIN-008** Environment-configurable externally exposed ports.
- **FIN-009** Structured logging and request/correlation IDs.
- **FIN-010** Initial CI quality gate.
- **FIN-011** Developer onboarding documentation.
- **FIN-012** Basic authentication foundation for later RBAC.

No Sprint 1 story is authorized for implementation until Sprint 0 is approved.
