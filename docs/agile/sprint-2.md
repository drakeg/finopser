# Sprint 2 — Organization, RBAC, and CI Performance

## Goal

Implement the organization hierarchy, project scope, server-side RBAC, privileged-action audit logging, and a basic management surface while preserving the Sprint 1 Docker deployment path.

## Scope

Tracked by GitHub Issue #4. AWS account onboarding, cloud inventory, cost ingestion, compliance evaluation, enforcement, and production AWS infrastructure remain out of scope.

## Roles

Managed roles are Platform Administrator, Cloud Administrator, FinOps Analyst, Security / Compliance Engineer, Project Owner, and Auditor. Platform and Cloud Administrators may mutate organization/project data. Other authenticated managed roles are read-only at this stage. Only Platform Administrators may change managed role assignments.

## CI and Docker performance

CI performance is a nonfunctional requirement. Sprint 2 keeps backend, frontend, and Docker jobs parallel for fast failure feedback, caches package downloads, builds the backend image once for the API/worker/scheduler services, and uses cache-mount-friendly Dockerfiles. Smoke testing remains intentionally narrow: successful full-stack startup plus UI and readiness probes.

## Acceptance

- recursive organization nodes and projects are persisted and API-accessible
- cross-organization parent/project relationships are rejected
- unsafe organization/project operations require Platform or Cloud Administrator role
- role assignment requires Platform Administrator role
- privileged changes produce audit events
- Docker-first startup remains supported
- CI retains lint, migration, test, frontend build, and full-stack smoke coverage
