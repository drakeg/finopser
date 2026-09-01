# Sprint 16 — Reporting and export

## Goal

Provide tenant-safe reporting and deterministic export of persisted Finopser evidence without coupling reporting to cloud-provider calls or a paid external reporting service.

## Reporting foundation slice

- Adds a report catalog service boundary independent of HTTP presentation.
- Adds a first `resource-inventory` report using normalized persisted `CloudResource` evidence.
- Adds deterministic CSV columns for account, provider, provider resource ID, resource type, name, region, state, active state, and last-seen timestamp.
- Applies tenant scope through the existing organization scoping helper using the resource's cloud-account ownership.
- Supports optional account, resource type, and active-state filters.
- Caps synchronous exports at 5,000 rows and reports truncation through response metadata; future large/background generation remains an explicit extension point.
- Records `report.export` audit events for tenant exports without placing CSV content in the audit log.
- Does not call AWS or any cloud provider during report generation.

## API

- `GET /api/reports/` — report catalog.
- `GET /api/reports/resource-inventory.csv` — resource inventory CSV.

Resource inventory filters:

- `account=<cloud-account-id>`
- `resource_type=<normalized-resource-type>`
- `active=true|false`

CSV responses include report code, row count, truncation state, and generated timestamp in `X-Finopser-*` headers.

## Safety and cost gate

No paid BI/reporting SaaS, external dashboard service, email service, production AWS reporting resource, or recurring spend is enabled. Reporting reads only existing application persistence.

## Next slices

- Financial/cost report family.
- Governance, recommendation/remediation, and audit report families with entitlement enforcement.
- Operational-console Reports workspace with filters, metadata preview, and downloads.
- Background/scheduled generation only if bounded synchronous reporting becomes insufficient.
