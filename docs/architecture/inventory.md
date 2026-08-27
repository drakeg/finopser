# Resource Inventory Architecture

Sprint 4 introduces Finopser's normalized resource inventory while preserving the OBSERVE-only safety model.

## Flow

1. An administrator explicitly requests inventory sync for a previously validated cloud account.
2. The core inventory service selects the registered provider adapter.
3. The AWS adapter assumes the account role with STS and performs read/list/describe operations only.
4. Provider-specific responses are converted to `ResourceRecord` objects before returning to core code.
5. Core inventory code upserts `CloudResource` rows using provider + cloud account + provider resource ID as the stable identity.
6. A fully successful sync marks previously active resources not seen in that run as inactive. A partial sync never marks unseen resources inactive because a service-level permission/error could otherwise create false stale results.
7. Every run is retained as an `InventorySync` record with counts, timestamps, status, and sanitized errors.

## Initial AWS coverage

- EC2 instances
- RDS DB instances
- S3 buckets
- Lambda functions
- ECS clusters and services

AWS API response shapes do not leak into the core inventory model. Provider-specific details belong in normalized metadata/tags fields.

## Safety

Inventory discovery has no create/update/delete AWS calls. Docker startup, health checks, page loads, and account listing do not trigger AWS discovery. Sync is explicit and requires a cloud account whose connection status is `valid`.

## Future evolution

The synchronous/manual API is intentional for Sprint 4. A later Sprint can move execution behind Celery and introduce scheduling while preserving the same inventory records and sync-history contract.
