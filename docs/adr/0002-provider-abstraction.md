# ADR-0002 — Provider abstraction with AWS first

**Status:** Accepted

## Context

The initial product will support AWS, but the long-term product may support Azure, GCP, OCI, SaaS, and on-premises data sources.

## Decision

Cloud-provider-specific SDK calls, identifiers, and implementation details will live behind provider interfaces. Core business logic will use normalized domain models and provider capabilities. AWS is the first provider implementation, not the platform architecture.

## Consequences

- Provider-specific behavior requires adapters and normalization.
- The initial implementation may carry some abstraction cost.
- Future provider additions should not require broad rewrites of core business logic.
- Optional capabilities may differ by provider and must be explicitly represented rather than hidden behind fragile conditionals.
