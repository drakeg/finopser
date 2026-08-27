# Sprint 0 — Product & Architecture Foundation

## Status

**IN PROGRESS**

## Sprint Goal

Establish a complete, reviewable source of truth for a Docker-first, AWS-ready cloud governance and FinOps platform inspired by the useful workflows of products such as Kion, without copying branding or proprietary implementation.

## Authorization Boundary

Sprint 0 authorizes documentation, architecture, backlog definition, standards, and project scaffolding only.

The following are **not authorized during Sprint 0**:

- product feature implementation;
- AWS infrastructure deployment;
- creation or modification of customer cloud resources;
- paid cloud services;
- recurring cloud spend;
- destructive or enforcement automation.

## Sprint 0 Deliverables

- Product vision and scope
- Personas and terminology
- Epic backlog and roadmap
- Definition of Ready
- Definition of Done
- Architecture overview
- Provider abstraction
- Organizational and inheritance model
- Initial domain model
- Security architecture
- Observe → Recommend → Enforce model
- Docker-first / AWS-ready deployment direction
- Testing strategy
- CI quality policy
- ADR register and initial decisions
- Sprint 1 candidate backlog
- Sprint 1 readiness and acceptance gate

## Sprint 1 Acceptance Gate

Sprint 1, when authorized, will establish the application foundation. A clean environment should ultimately be able to perform approximately:

```bash
git clone <repository>
cp .env.example .env
docker compose up --build
```

and obtain:

- a working web UI;
- a working backend/API;
- PostgreSQL;
- Redis;
- background worker infrastructure;
- health checks;
- persistent local storage;
- documented, environment-configurable exposed ports;
- initial authentication foundation;
- CI passing.

Sprint 1 must not silently fall back to SQLite or require AWS services to run locally.

## Readiness Gate

Sprint 0 is ready for approval when the following are represented in the repository and internally consistent:

- [x] Product vision
- [x] Scope and early non-goals
- [x] Personas
- [x] Core architectural principles
- [x] Organizational hierarchy direction
- [x] Provider abstraction direction
- [x] Initial domain model
- [x] Security model
- [x] Observe/Recommend/Enforce model
- [x] Docker-first deployment direction
- [x] AWS production direction
- [x] Epic backlog
- [x] Definition of Ready
- [x] Definition of Done
- [x] Testing/CI policy
- [x] ADR register
- [x] Sprint 1 candidate backlog and acceptance gate

Approval of this checklist authorizes Sprint 1 planning and implementation; it does not authorize later AWS deployment or paid infrastructure.
