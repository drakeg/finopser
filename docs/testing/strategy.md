# Testing and CI Strategy

## Testing Layers

### Unit Tests

Business rules, domain services, serializers/validation, provider normalization logic, and other isolated behavior should have fast unit coverage.

### Integration Tests

Integration coverage should validate boundaries such as:

- PostgreSQL persistence;
- Redis/cache/queue integration;
- API endpoints;
- authentication/authorization;
- provider adapters with deterministic mocks/fakes;
- background jobs;
- migrations.

### End-to-End / Smoke Tests

Critical user journeys should eventually receive end-to-end coverage. Sprint 1 should at minimum establish health/smoke checks proving the composed application is reachable and its required dependencies are healthy.

### Regression Tests

Defect fixes should include a test that fails before the fix and passes after it whenever practical.

## Provider Testing

Automated CI must not depend on live customer cloud accounts.

Provider adapters should support deterministic tests using fakes, fixtures, and SDK stubbing. Explicit live-account verification may be added later as a separately authorized environment/test class.

## Initial CI Quality Gate

Before merge to `main`, applicable changes should pass:

- formatting checks;
- linting;
- static type checking;
- backend tests;
- frontend tests;
- migration checks;
- Docker image/build validation;
- dependency vulnerability scanning;
- secret scanning;
- SAST;
- container image scanning;
- documentation checks where practical.

## Candidate Tools

Final tool selection is implementation-dependent, but likely candidates include:

- Ruff
- mypy
- pytest
- ESLint
- TypeScript compiler
- Gitleaks
- Semgrep
- Trivy
- Dependabot

Tool choice and enforcement thresholds should be explicit in repository configuration rather than tribal knowledge.

## Warnings and Failures

New unexplained warnings are treated as defects, not normal successful output. Security findings must have documented severity thresholds and exception handling rather than being ignored ad hoc.

## Pull Request Scope

CI complements rather than replaces review. PRs should remain narrowly scoped to approved backlog items and should not contain unrelated cleanup, redesign, or opportunistic feature work.
