# Domain Model

## Organization hierarchy

`Organization` is the top-level governance container. `OrganizationNode` is recursively nestable through `parent`, allowing business units, departments, teams, environments, and future node types without schema redesign. `Project` belongs to one organization and one node in that same organization.

The model intentionally prepares for inheritance: future policies, budgets, access rules, and compliance controls can be attached at an organization or node scope and resolved down the parent chain.

## Identity and RBAC

Sprint 2 uses Django users and groups as the identity and managed-role foundation. Managed roles are Platform Administrator, Cloud Administrator, FinOps Analyst, Security / Compliance Engineer, Project Owner, and Auditor. Organization/project mutation is limited to Platform and Cloud Administrators; role assignment is limited to Platform Administrators. All authorization is enforced server-side.

## Audit

`AuditEvent` captures actor, action, object type/id/representation, structured metadata, and timestamp for privileged governance mutations. Audit events are read-only through both the API and Django administration.

## Future core entities

CloudAccount, CloudResource, CostRecord, Budget, Policy, ComplianceControl, ComplianceFinding, Recommendation, Remediation, and AutomationRun remain planned domain entities and will be introduced only in their approved Sprints.
