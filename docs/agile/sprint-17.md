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

## Completed slice — operational integrity visibility

- Enhance the existing Administration workspace rather than adding a new navigation surface.
- Show the latest audit checkpoint status as verified, invalid, or unverified.
- Show covered event count, unchecked newer events, algorithm, and checkpoint event identifier.
- Allow manager-authorized users to create a checkpoint from the console through the existing `POST /api/audit-integrity/` endpoint.
- Allow users to re-run verification without creating new evidence.
- Keep the UI explicit that application-level checkpoints are tamper evidence and not independently anchored WORM storage.

## Final slice — export integrity context

- Snapshot the current tenant audit-integrity result before recording the export action itself.
- Attach integrity status, algorithm, covered-event count, unchecked-event count, and checkpoint event identifier to audit CSV response headers.
- Keep checkpoint metadata and arbitrary audit metadata out of CSV rows, preserving the existing narrow evidence-export surface.
- Make the integrity context machine-readable without changing the stable audit CSV columns.

## Integrity, retention, and recovery semantics

A checkpoint proves that the application-visible audit rows covered by that checkpoint still match the canonical digest captured when the checkpoint was created. Existing/legacy audit rows require no rewrite: the first checkpoint deterministically covers the tenant history that already exists at checkpoint time.

Audit events are append-only through supported product APIs and Django admin behavior. Sprint 17 does not introduce automatic deletion or a retention timer; operators remain responsible for database backup and retention policy appropriate to their deployment.

An `invalid` checkpoint is evidence of a mismatch, not something Finopser silently repairs. Recovery should preserve the affected database state for investigation, compare against trusted backups or independently retained exports, restore only through an operator-controlled recovery process, and create a new checkpoint after the recovered history has been reviewed. Newer events after a valid checkpoint are reported as unchecked rather than being implied valid.

Application-level checkpoints are tamper-evident, not independently anchored WORM evidence. A database administrator with unrestricted write access could alter both evidence and checkpoint rows. A future provider-neutral evidence sink can anchor checkpoint digests or exports to external WORM/SIEM/object-lock storage when an operator explicitly enables and funds that infrastructure.

Trusted state transitions that require audit evidence should commit their authoritative state and audit record atomically where they share the same database transaction boundary. External or secondary delivery such as notifications remains best-effort and outside that authoritative transaction.

## Safety / cost gate

No SIEM SaaS, CloudTrail Lake, S3 Object Lock resource, paid observability platform, production AWS resource, or recurring spend is authorized.

## Definition of done

- Tenant-scoped audit evidence can be checkpointed and verified deterministically.
- Modified/deleted covered evidence produces an invalid result.
- Newer uncovered evidence is reported explicitly rather than silently treated as verified.
- Cross-tenant history is excluded from tenant checkpoint calculations.
- Existing history can be checkpointed without destructive backfill or row rewriting.
- Manager-only checkpoint creation preserves existing RBAC semantics.
- Existing audit APIs/admin behavior remains read-only.
- Representative trusted subscription state changes cannot commit without their corresponding audit evidence.
- The operational console exposes integrity status and checkpoint creation without external dependencies.
- Audit evidence exports expose bounded integrity context without broadening sensitive metadata.
- Retention, recovery, and future independently anchored WORM/SIEM extension semantics are documented.
- Backend/frontend/Docker CI remains green.
