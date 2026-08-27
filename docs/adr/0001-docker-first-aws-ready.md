# ADR-0001 — Docker-first, AWS-ready architecture

**Status:** Accepted

## Context

finopser must be easy to run locally for development/testing while retaining a clear path to production deployment on AWS.

## Decision

The complete core application will run locally with Docker Compose and without requiring managed AWS services. Production architecture will be designed so equivalent responsibilities can map to AWS managed services where appropriate.

## Consequences

- Local development remains inexpensive and reproducible.
- Business logic may not assume ECS, RDS, ElastiCache, S3, Secrets Manager, or CloudWatch are always present.
- Environment-specific integrations require clean boundaries/configuration.
- AWS deployment remains a later, explicitly authorized activity.
