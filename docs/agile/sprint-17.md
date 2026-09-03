# Sprint 17 — Audit Evidence Integrity and Hardening

## Sprint goal

Complete the P0 Audit & Evidence epic by hardening Finopser's existing tenant-owned audit history with verifiable integrity semantics while remaining self-contained in Docker/local deployments.

## Issue

- #64 — Sprint 17: Audit evidence integrity and hardening

## Existing foundation

Finopser already provides tenant-owned `AuditEvent` records, read-only tenant-scoped audit APIs, read-only Django admin behavior for audit events, and bounded CSV evidence export. Sprint 17 extends this foundation rather than replacing it.

## Completed slice — integrity checkpoints

- Add deterministic SHA-256 checkpoints over ordered, tenant-scoped audit history.
- Canonicalize event identity, tenant ownership, actor, action, target, metadata, and creation timestamp before hashing.
- Store checkpoint digest/count/coverage metadata as a normal immutable audit event.
- Expose `GET /api/audit-integrity/` to verify the latest checkpoint and report uncovered newer events.
- Expose manager-only `POST /api/audit-integrity/` to create a new checkpoint.
- Keep tenant histories independent; a modification in another organization must not affect the current tenant's verification result.
- Detect deletion/modification of checkpoint-covered evidence through count/digest mismatch.

## Completed slice — trusted billing audit atomicity

- Persist the tenant-owned audit event for trusted Stripe subscription create/update/delete state changes inside the same database transaction as the `BillingEvent` and `Subscription` mutation.
- Keep webhook retries idempotent: an already processed provider event does not create a second audit event.
- If audit evidence cannot be written, roll back the provider event marker and subscription mutation together so a retry can safely process the event again.
- Keep billing attention notifications outside the state/evidence transaction; notification delivery failure must not invalidate trusted subscription state or its audit evidence.
- Preserve the existing test-mode-only Stripe safety gate and provider-neutral billing boundary.

## Current slice — operational integrity visibility

- Enhance the existing Administration workspace rather than adding a new navigation surface.
- Show the latest audit checkpoint status as verified, invalid, or unverified.
- Show covered event count, unchecked newer events, algorithm, and checkpoint event identifier.
- Allow manager-authorized users to create a checkpoint from the console through the existing `POST /api/audit-integrity/` endpoint.
- Allow users to re-run verification without creating new evidence.
- Keep the UI explicit that application-level checkpoints are tamper evidence and not independently anchored WORM storage.

## Integrity semantics

A checkpoint proves that the application-visible audit rows covered by that checkpoint still match the canonical digest captured when the checkpoint was created. It is tamper-evident at the application/database-record level; it is not a substitute for independently anchored WORM storage because a database administrator with unrestricted write access could alter both evidence and checkpoint rows.

Trusted state transitions that require audit evidence should commit their authoritative state and audit record atomically where they share the same database transaction boundary. External or secondary delivery such as notifications remains best-effort and outside that authoritative transaction.

Future Sprint 17 slices may add audit-export integrity/checkpoint context and external/WORM retention/recovery documentation.

## Safety / cost gate

No SIEM SaaS, CloudTrail Lake, S3 Object Lock resource, paid observability platform, production AWS resource, or recurring spend is authorized.

## Definition of done

- Tenant-scoped audit evidence can be checkpointed and verified deterministically.
- Modified/deleted covered evidence produces an invalid result.
- Newer uncovered evidence is reported explicitly rather than silently treated as verified.
- Cross-tenant history is excluded from tenant checkpoint calculations.
- Manager-only checkpoint creation preserves existing RBAC semantics.
- Existing audit APIs/admin behavior remains read-only.
- Representative trusted subscription state changes cannot commit without their corresponding audit evidence.
- The operational console exposes integrity status and checkpoint creation without external dependencies.
- Backend/frontend/Docker CI remains green.
