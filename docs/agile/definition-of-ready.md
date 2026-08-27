# Definition of Ready

A backlog item may enter an implementation Sprint only when all applicable conditions below are satisfied.

## Required

- User or operational value is identified.
- Acceptance criteria are explicit and testable.
- Dependencies are known.
- Architectural dependencies or unresolved ADRs are identified.
- Security impact has been considered.
- Authorization and least-privilege implications have been considered.
- Data-model and migration impact has been considered.
- Provider-specific versus provider-neutral behavior is clear.
- Testing requirements are defined.
- Documentation requirements are defined.
- Logging/audit requirements are defined where applicable.
- Failure and rollback behavior is understood for cloud-changing operations.
- The item is small enough to complete within one Sprint.
- Any required design or UX decision is sufficiently resolved to implement.

## Cloud-Changing Stories

Any story capable of changing cloud infrastructure must additionally define:

- operating mode: OBSERVE, RECOMMEND, or ENFORCE;
- required provider permissions;
- blast radius;
- idempotency expectations;
- dry-run or recommendation behavior where feasible;
- audit event requirements;
- error and partial-failure handling;
- explicit authorization boundary.

If these conditions are not satisfied, the item remains in refinement and may not enter the Sprint backlog.
