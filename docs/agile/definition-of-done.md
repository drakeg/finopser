# Definition of Done

A story is not complete merely because it works locally. All applicable conditions below must be satisfied before merge.

## Functional Completion

- Acceptance criteria are satisfied.
- No unrelated functionality is changed.
- Error paths and failure states are handled.
- Any provider behavior remains behind the appropriate abstraction.

## Quality

- Unit tests are added or updated.
- Integration tests are added where appropriate.
- Regression coverage is added for defect fixes.
- Formatting passes.
- Linting passes.
- Static type checking passes.
- Existing automated tests remain green.
- No unexplained warnings are introduced.

## Security

- Secret scanning passes.
- Dependency vulnerability scanning passes within the project's documented policy.
- SAST passes within the project's documented policy.
- Container scanning passes when containers are affected.
- Authorization is enforced server-side.
- Secrets and credentials are not logged or committed.
- Cloud-changing behavior satisfies Observe/Recommend/Enforce requirements.

## Deployment

- Docker build succeeds when application code or dependencies change.
- Required health checks pass.
- Environment changes are documented in `.env.example` without secrets.
- Database migrations are included and tested where applicable.

## Documentation

- User documentation is updated when behavior changes.
- Developer documentation is updated when setup or architecture changes.
- API documentation is updated when APIs change.
- ADRs are added or superseded when architectural decisions change.
- `CHANGELOG.md` is updated when appropriate.

## Review and Merge

- CI is green.
- The PR is reviewable and scoped to the active backlog item(s).
- The PR contains no unexplained unrelated changes.
- Required review/acceptance has occurred.
- The change is merged to `main` through the agreed PR workflow.
