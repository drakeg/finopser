# ADR-0005 — PostgreSQL as the primary database

**Status:** Accepted

## Context

finopser will store relational organizational data, cloud-account metadata, resource inventory, costs, findings, policies, budgets, recommendations, and audit records. Development behavior should closely match production behavior.

## Decision

PostgreSQL is the primary relational database from the beginning. The application will not use SQLite as a silent development fallback.

## Consequences

- Local Docker Compose includes PostgreSQL.
- Migrations and integration tests exercise PostgreSQL semantics.
- Developers require the composed database service or an explicitly configured compatible PostgreSQL instance.
- Production can map naturally to RDS PostgreSQL without changing application persistence semantics.
