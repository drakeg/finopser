# Coding Standards

These standards apply to every Finopser sprint and pull request.

## Scope and design

- Implement only the active backlog item and its acceptance criteria; avoid unrelated refactors.
- Prefer small, cohesive modules and explicit interfaces over large cross-cutting changes.
- Keep provider-specific behavior behind provider/adaptor boundaries.
- Preserve tenant isolation, deny-by-default authorization, and the Observe → Recommend → Approve → Execute separation.
- Cloud-changing behavior must remain disabled unless the sprint explicitly authorizes it.
- Never introduce paid services, recurring spend, production infrastructure, or external delivery implicitly.

## Python / Django

- Follow Ruff formatting/lint rules and the repository's mypy configuration.
- Use explicit validation at API/service boundaries.
- Enforce authorization and tenant scope server-side; frontend visibility is never an authorization control.
- Keep migrations aligned with model state and test migration consistency.
- Do not log, audit, return, or persist secrets, credentials, tokens, raw provider responses, or sensitive exception text unless an approved design explicitly requires a safe representation.
- Catch broad exceptions only at deliberate isolation boundaries; persist/return sanitized outcomes.

## TypeScript / React

- Keep API response types explicit.
- Treat backend authorization and entitlement decisions as authoritative.
- Surface recoverable errors without destroying unrelated page state.
- Do not embed secrets or provider credentials in frontend state/build output.
- Prefer focused components/helpers and accessible native controls over duplicated interaction logic.

## Tests

- Add regression coverage for defects and acceptance coverage for new behavior.
- Prefer extending a small number of cohesive test modules over one-file-per-case test sprawl.
- Tests must be deterministic and must not require live cloud accounts, external IdPs, paid APIs, or production services.
- Use fakes/mocks at external/provider boundaries; test the real application policy around those boundaries.
- Verify tenant isolation and negative authorization paths whenever scoped data or privileged actions change.

## Commits and pull requests

- Use focused, imperative commit messages.
- Keep PRs tied to the active issue/sprint slice and describe safety/cost boundaries when relevant.
- Do not merge with failing required CI.
- When CI fails, diagnose the exact failing job/step before changing code; do not make speculative fixes.
- Documentation, tests, migrations, and examples must change in the same PR when behavior requires them.

## Documentation maintenance

Every sprint must keep these artifacts current when applicable:

- `docs/agile/sprint-<n>.md` — sprint goal, slices, acceptance, safety/cost boundary, completion notes.
- `docs/agile/product-backlog.md` — material reprioritization or newly discovered work.
- `docs/agile/definition-of-ready.md` and `definition-of-done.md` — process changes.
- `docs/testing/strategy.md` — test/CI strategy changes.
- architecture/security/ADR documentation — architectural or trust-boundary changes.
- `README.md` / getting-started documentation — user/developer workflow changes.

Documentation is part of the implementation, not a post-sprint cleanup task.
