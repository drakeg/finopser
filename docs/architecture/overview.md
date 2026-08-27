# Architecture Overview

## Architectural Goals

finopser is designed as a self-hosted control plane with Docker-first local deployment and an AWS-ready production topology.

## Core Topology

```text
Browser
   |
   v
Frontend
   |
   v
Application API
   |-- PostgreSQL
   |-- Redis
   |-- Background Workers / Scheduler
   `-- Provider Adapters
        |-- AWS
        |-- Azure (future)
        |-- GCP (future)
        `-- OCI (future)
```

## Architectural Principles

### Docker-first

The complete core application must be runnable locally with Docker Compose and without managed AWS dependencies.

### AWS-ready, not AWS-dependent

Production components should map cleanly to AWS services such as ECS, RDS, ElastiCache, S3, Secrets Manager, and CloudWatch, but local execution must use interchangeable local equivalents.

### API-first

The primary web interface consumes application APIs rather than relying on privileged UI-only behavior. Public API stabilization may occur later, but core business operations should be represented as application services/APIs from the beginning.

### Provider abstraction

Provider-specific SDK calls and resource semantics remain inside provider modules. Business logic consumes normalized interfaces and domain models.

A conceptual interface includes capabilities such as:

```text
discover_accounts
validate_connection
inventory_resources
ingest_costs
evaluate_controls
apply_policy
grant_access
provision_account
```

Not every provider must implement every optional capability.

### Auditability

Governance-relevant and privileged application changes emit audit events. Audit requirements are part of feature design, not an afterthought.

### Safe cloud mutation

Cloud changes are governed by the Observe → Recommend → Enforce model defined in the security documentation.

## Initial Technology Direction

The Sprint 0 recommendation is:

- Backend: Python + Django + Django REST Framework
- Database: PostgreSQL
- Background processing: Celery
- Queue/cache: Redis
- Frontend: React + TypeScript
- Visualization: a mature charting library such as Apache ECharts

These choices remain subject to ADR approval before implementation where the ADR is not yet accepted.

## Repository Direction

```text
/
|-- backend/
|-- frontend/
|-- docs/
|   |-- adr/
|   |-- agile/
|   |-- architecture/
|   |-- deployment/
|   |-- security/
|   `-- testing/
|-- docker/
|-- scripts/
|-- tests/
|-- infrastructure/
|   `-- terraform/
|-- compose.yaml
|-- .env.example
|-- README.md
|-- SECURITY.md
|-- CONTRIBUTING.md
`-- CHANGELOG.md
```

Terraform modules, when introduced, keep variable declarations in `variables.tf` and output declarations in `outputs.tf` rather than embedding them in `main.tf`.
