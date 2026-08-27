# Local Development — Getting Started

## Prerequisites

- Git
- Docker Engine / Docker Desktop with Compose v2

No AWS account is required for Sprint 1.

## Start the platform

```bash
git clone https://github.com/drakeg/finopser.git
cd finopser
cp .env.example .env
```

Before sharing or exposing the deployment, change `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` in `.env`.

Start the complete local stack:

```bash
docker compose up --build
```

By default:

- Web UI: `http://localhost:8080`
- Backend/API: `http://localhost:8000/api/`
- Liveness: `http://localhost:8000/api/health/`
- Readiness: `http://localhost:8000/api/ready/`
- Django admin: `http://localhost:8000/admin/`

## Change ports

Edit `.env`:

```dotenv
APP_PORT=8080
BACKEND_PORT=8000
```

If `APP_PORT` changes, also update `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to match the browser-facing origin.

PostgreSQL and Redis are intentionally internal-only in the default Compose topology; they are not published to the host.

## Authentication foundation

Django authentication and session infrastructure are enabled. Sprint 1 does not yet provide the final product login experience or RBAC model.

To create a local administrative user:

```bash
docker compose exec backend python manage.py createsuperuser
```

The API session endpoint is available at `/api/auth/session/`.

## Stop the platform

```bash
docker compose down
```

Persistent PostgreSQL and Redis volumes are retained. To intentionally delete local data:

```bash
docker compose down -v
```

## Troubleshooting

Inspect service state:

```bash
docker compose ps
```

Inspect logs:

```bash
docker compose logs -f backend worker scheduler frontend
```

The readiness endpoint reports PostgreSQL and Redis connectivity independently. A `503` readiness response means at least one required dependency is unavailable.
