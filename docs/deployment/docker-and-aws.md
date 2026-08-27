# Deployment Model

## Local Development and Testing

Docker Compose is the mandatory local deployment target for the complete core application.

The intended topology is:

```text
frontend
backend
worker
scheduler
postgres
redis
```

A reverse proxy may be added when useful, but the core platform must not require managed cloud services merely to launch locally.

## Configuration

Externally exposed development ports and environment-dependent settings must be configurable through environment variables and documented in `.env.example`.

Example direction:

```dotenv
APP_PORT=8080
POSTGRES_PORT=5432
REDIS_PORT=6379
```

No secret values belong in `.env.example`.

## Persistence

PostgreSQL and any other stateful local services must use documented persistent volumes by default so normal container restarts do not silently destroy development data.

## Production AWS Direction

The application architecture should map cleanly to AWS managed services where beneficial:

```text
Application containers -> ECS
PostgreSQL            -> RDS PostgreSQL
Redis                 -> ElastiCache
Artifacts/reports     -> S3
Secrets               -> Secrets Manager / KMS
Logs/metrics          -> CloudWatch
```

This mapping is a production direction, not a Sprint 0 deployment authorization.

## Separation of Concerns

The application must use abstractions/configuration that allow local and production implementations to differ without branching business logic throughout the codebase.

Examples:

- local environment variables vs. production secret stores;
- local PostgreSQL container vs. RDS;
- local Redis container vs. ElastiCache;
- local filesystem development artifacts vs. S3-backed production artifacts where applicable.

## Infrastructure as Code

AWS infrastructure will eventually be defined as code. Terraform is the preferred direction unless superseded by an ADR.

Terraform modules must keep:

- variable declarations in `variables.tf`;
- outputs in `outputs.tf`;
- resources/data sources primarily in `main.tf` or purpose-specific resource files.

## Cost Safety

No AWS production resources or recurring spend are authorized by Sprint 0. AWS deployment work requires a later explicitly approved Sprint/backlog item with cost implications documented before activation.
