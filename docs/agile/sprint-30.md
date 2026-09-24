# Sprint 30 — Reporting and Export Completion

## Sprint goal

Complete E015 by restoring the previously implemented interactive reporting experience, hardening the report catalog/download contract, and then adding safe local scheduling/history boundaries without implicit external delivery.

## Issues

- #136 — Sprint 30: Reporting and export completion
- #137 — Slice 1: Report catalog and download workspace
- #139 — Slice 2: Durable report schedules and local generation metadata

## Slice 1 — Report workspace regression restoration

Repository review found that Sprint 16 had documented and completed an interactive Reports workspace, while the current frontend had regressed to a static placeholder. Sprint 30 treats this as a regression rather than creating a competing reporting architecture.

The backend report catalog now includes the authoritative authenticated download endpoint for every entitlement-visible report. Catalog entries remain metadata-only: code, name, description, format, target, feature where applicable, and endpoint. They do not expose tenant data or credentials.

The Reports page again loads the entitlement-filtered catalog and provides explicit CSV downloads. Downloads use the existing authenticated endpoints, so tenant scoping, report entitlements, audit logging, deterministic schemas, and the 5,000-row synchronous cap remain backend-authoritative.

Download failures are surfaced as recoverable UI errors. Scheduled generation and external delivery remain visibly disabled and are not implied by the restored workspace.

## Slice 2 — Durable scheduling boundary

Report schedules are now durable tenant-scoped intent records with a name, supported report code, cadence, active state, creator, and lifecycle timestamps. Managers can create, enable, and disable schedules; authenticated workspace members can inspect schedules only when the underlying report remains entitled to them.

The slice deliberately does **not** register Celery Beat tasks, execute reports automatically, or deliver reports externally. It establishes the durable configuration boundary without silently turning configuration into execution.

Report generation history stores metadata only: report code, schedule reference, success/failure state, row count, truncation flag, requester, and generation time. Exported CSV bodies are not persisted in the history model. History is tenant-scoped and entitlement-filtered.

Schedule create/enable/disable actions are audited with sanitized report/cadence metadata.

## Engineering-process documentation

Sprint 30 also closes repository-level process documentation debt:

- `docs/agile/sprint-process.md` defines sprint planning, slicing, verification, merge/continuation, completion, and regression handling.
- `docs/development/coding-standards.md` defines Python/Django, TypeScript/React, security, testing, PR, and documentation standards.
- README links the durable process documents rather than claiming the project is still in Sprint 1.
- local getting-started guidance no longer describes authentication/provider boundaries as Sprint 1-only.

These documents apply to all future Finopser development.

## Safety / cost gate

No paid BI/reporting service, hosted scheduler, automatic external delivery, production infrastructure, recurring spend, or live provider call is introduced. Downloads are explicit authenticated user actions over persisted application evidence.
