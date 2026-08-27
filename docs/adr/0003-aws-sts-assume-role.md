# ADR-0003 — AWS access through STS AssumeRole

**Status:** Accepted

## Context

finopser requires cross-account AWS visibility and, later, optionally authorized actions. Long-lived IAM user access keys stored by the application would create unnecessary credential risk.

## Decision

AWS account onboarding will be designed around IAM roles assumed through AWS STS. Appropriate trust policies, external IDs where applicable, and least-privilege permission sets will be used. Long-lived IAM user access-key/secret-key pairs are not the standard integration model.

## Consequences

- AWS onboarding must create or reference suitable IAM roles.
- The platform must handle STS session expiration and renewal correctly.
- Permissions should be capability-scoped and expand only when explicitly authorized.
- Local application secrets do not need to contain permanent credentials for every managed AWS account.
