# Sprint 4 — AWS Resource Inventory & Discovery

Tracker: GitHub Issue #12

## Goal

Provide explicit, read-only AWS resource discovery and a normalized inventory model suitable for operational dashboards and later FinOps/compliance features.

## Included

- provider resource discovery contract
- AWS discovery for EC2, RDS, S3, Lambda, and ECS
- normalized CloudResource persistence
- InventorySync history/status
- manual validated-account sync API
- resource filtering API
- stale/inactive lifecycle semantics
- mocked tests requiring no AWS credentials
- Resources/dashboard UI visibility
- architecture and developer documentation

## Excluded

No scheduled polling, resource mutation, remediation, compliance evaluation, cost ingestion, account vending, AWS deployment, or paid service activation.

## CI / Docker constraint

Sprint 4 must reuse the existing backend/frontend/Docker jobs, dependency caches, and shared backend image. Inventory tests run inside the existing backend job; no additional CI job is warranted.
