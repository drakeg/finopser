# finopser

<!-- madmallard-badges:start -->
[![Python](https://img.shields.io/badge/Python-backend-3776AB?logo=python&logoColor=white)](backend/requirements.txt) [![Django](https://img.shields.io/badge/Django-6.1.3-092E20?logo=django&logoColor=white)](backend/requirements.txt) [![React](https://img.shields.io/badge/React-frontend-149ECA?logo=react&logoColor=white)](frontend/package.json) [![TypeScript](https://img.shields.io/badge/TypeScript-frontend-3178C6?logo=typescript&logoColor=white)](frontend/package.json) [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)](compose.yaml) [![Redis](https://img.shields.io/badge/Redis-8-DC382D?logo=redis&logoColor=white)](compose.yaml)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](compose.yaml) [![CI](https://github.com/drakeg/finopser/actions/workflows/ci.yml/badge.svg)](https://github.com/drakeg/finopser/actions/workflows/ci.yml) [![Tests](https://img.shields.io/badge/Tests-CI%20backend%20%7C%20frontend%20%7C%20CLI-555?logo=githubactions)](https://github.com/drakeg/finopser/actions/workflows/ci.yml) [![Releases](https://img.shields.io/github/v/release/drakeg/finopser?display_name=tag)](https://github.com/drakeg/finopser/releases)
[![Issues](https://img.shields.io/github/issues/drakeg/finopser)](https://github.com/drakeg/finopser/issues) [![Pull requests](https://img.shields.io/github/issues-pr/drakeg/finopser)](https://github.com/drakeg/finopser/pulls) [![Security advisories](https://img.shields.io/badge/Security-advisories-555?logo=github)](https://github.com/drakeg/finopser/security/advisories)
<!-- madmallard-badges:end -->

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

AWS onboarding and governance functionality have advanced beyond the initial foundation. Azure registration, runtime-only identity and isolated subscription lookup are under active Sprint 32 development; production Azure validation, inventory and cost sync remain disabled until explicitly authorized and tested.

## Project documentation

- [Sprint roadmap](SPRINTS.md)
- [Prioritized backlog](BACKLOG.md)
- [Agent standards](AGENTS.md)
- [Contributing](CONTRIBUTING.md)
- [Release policy](RELEASES.md)
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
