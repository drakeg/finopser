# Sprint 1 — Application Foundation

**Tracker:** GitHub Issue #2  
**Status:** In implementation  
**Scope authority:** Sprint 0 documentation merged in PR #1

## Sprint Goal

Deliver a production-shaped local application foundation that can be started with Docker Compose and supports the application layers required for later cloud-management functionality.

## Included stories

- CCP-001 Repository implementation structure
- CCP-002 Django backend application
- CCP-003 PostgreSQL integration
- CCP-004 Redis integration
- CCP-005 Celery worker and scheduler infrastructure
- CCP-006 React/TypeScript frontend application shell
- CCP-007 Docker Compose stack
- CCP-008 Environment-configurable browser/API ports
- CCP-009 Structured logging and request correlation IDs
- CCP-010 CI quality gate
- CCP-011 Developer documentation
- CCP-012 Basic authentication/session foundation

## Explicitly excluded

- AWS deployment or AWS infrastructure
- AWS account onboarding
- AWS credentials or AssumeRole implementation
- resource inventory
- cost ingestion / FinOps data
- compliance evaluation
- policy enforcement
- remediation or cloud-changing automation
- paid service activation or recurring cloud spend

## Acceptance gate

A fresh clone must be able to copy `.env.example` to `.env`, run `docker compose up --build`, and obtain the web UI, API, PostgreSQL, Redis, worker, scheduler, health checks, persistent local storage, and configurable host ports.

Applicable Definition of Done checks must be green before the Sprint 1 PR is merged.
