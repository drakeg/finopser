# Sprint 17 — Audit Evidence Integrity and Hardening

## Sprint goal

Complete the P0 Audit & Evidence epic by hardening Finopser's existing tenant-owned audit history with verifiable integrity semantics while remaining self-contained in Docker/local deployments.

## Issue

- #64 — Sprint 17: Audit evidence integrity and hardening

## Existing foundation

Finopser already provides tenant-owned `AuditEvent` records, read-only tenant-scoped audit APIs, read-only Django admin behavior for audit events, and bounded CSV evidence export. Sprint 17 extends this foundation rather than replacing it.

## Initial slice — integrity checkpoints

- Add deterministic SHA-256 checkpoints over ordered, tenant-scoped audit history.
- Canonicalize event identity, tenant ownership, actor, action, target, metadata, and creation timestamp before hashing.
- Store checkpoint digest/count/coverage metadata as a normal immutable audit event.
- Expose `GET /api/audit-integrity/` to verify the latest checkpoint and report uncovered newer events.
- Expose manager-only `POST /api/audit-integrity/` to create a new checkpoint.
- Keep tenant histories independent; a modification in another organization must not affect the current tenant's verification result.
- Detect deletion/modification of checkpoint-covered evidence through count/digest mismatch.

## Integrity semantics

A checkpoint proves that the application-visible audit rows covered by that checkpoint still match the canonical digest captured when the checkpoint was created. It is tamper-evident at the application/database-record level; it is not a substitute for independently anchored WORM storage because a database administrator with unrestricted write access could alter both evidence and checkpoint rows.

Future Sprint 17 slices may add operational integrity UI, audit-export integrity fields/checkpoint context, trusted-workflow audit atomicity hardening, and external/WORM extension documentation.

## Safety / cost gate

No SIEM SaaS, CloudTrail Lake, S3 Object Lock resource, paid observability platform, production AWS resource, or recurring spend is authorized.

## Definition of done

- Tenant-scoped audit evidence can be checkpointed and verified deterministically.
- Modified/deleted covered evidence produces an invalid result.
- Newer uncovered evidence is reported explicitly rather than silently treated as verified.
- Cross-tenant history is excluded from tenant checkpoint calculations.
- Manager-only checkpoint creation preserves existing RBAC semantics.
- Existing audit APIs/admin behavior remains read-only.
- Backend/frontend/Docker CI remains green.
