# Contributing to Finopser

Read [AGENTS.md](AGENTS.md), [SPRINTS.md](SPRINTS.md), [BACKLOG.md](BACKLOG.md), and [release policy](RELEASES.md) before contributing. Follow the project's existing [coding standards](docs/development/coding-standards.md) and [sprint process](docs/agile/sprint-process.md).

Use a focused feature branch and a reviewable pull request with a linked sprint/backlog item, customer impact, acceptance criteria, tests, security considerations, rollback, and release impact. Prefer Conventional Commits. Keep documentation and tests synchronized with changes.

## Local validation

```bash
cp .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
```

Run backend quality checks with `ruff check backend`, `python backend/manage.py check`, and `python backend/manage.py test` in a correctly configured Python environment; run `npm test && npm run lint && npm run build` from `frontend/`. CI also exercises Docker Compose and CLI tests. Do not claim a local test passed unless it ran successfully.

For LAN access, configure `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` for the actual host/IP and port; never expose development credentials to an untrusted network.

Changes require passing CI and required review before merge. No credentials or customer data in issues, logs, or PRs. Do not add an open-source license without an explicit licensing decision.
