# finopser

Self-hosted cloud governance and FinOps platform, initially focused on AWS, with Docker-first local deployment and an AWS-ready architecture.

> **Project status:** Active iterative development — see the current numbered sprint under `docs/agile/`.

## Local quick start

```bash
cp .env.example .env
docker compose up --build
```

The default web UI is available at `http://localhost:8080`. Both the web and backend host ports are configurable in `.env`.

See [`docs/development/getting-started.md`](docs/development/getting-started.md) for setup and troubleshooting.

## Current safety boundary

Sprint 1 establishes the local application foundation only. No AWS credentials are required, and finopser cannot modify cloud resources in this sprint.

## Project documentation

- [Product vision](docs/agile/product-vision.md)
- [Product backlog](docs/agile/product-backlog.md)
- [Sprint process](docs/agile/sprint-process.md)
- [Coding standards](docs/development/coding-standards.md)
- [Definition of Ready](docs/agile/definition-of-ready.md)
- [Definition of Done](docs/agile/definition-of-done.md)
- [Architecture overview](docs/architecture/overview.md)
- [Domain model](docs/architecture/domain-model.md)
- [Security model](docs/security/security-model.md)
- [Testing strategy](docs/testing/strategy.md)
- [Sprint history](docs/agile/)
- [ADRs](docs/adr/README.md)
