# Sprint 16 — Reporting and Export

## Sprint goal

Turn persisted Finopser evidence into tenant-safe, useful reports and deterministic exports without adding an external reporting dependency.

## Issue

- #57 — Sprint 16: Reporting and export

## Initial stories

- **FIN-1601** Define a provider-neutral reporting service boundary and report catalog.
- **FIN-1602** Export normalized resource inventory as deterministic tenant-scoped CSV.
- **FIN-1603** Add financial/cost reporting and CSV export from persisted cost evidence.
- **FIN-1604** Add governance, recommendation/remediation, and audit report families while preserving feature entitlements.
- **FIN-1605** Replace the Reports placeholder with a report workspace for selection, filtering, preview metadata, and download.
- **FIN-1606** Add regression coverage for tenant isolation, filters, deterministic output, entitlement behavior, bounded synchronous generation, and no provider calls.
- **FIN-1607** Document synchronous limits and future background/scheduled-report extension points.

## Safety and cost gate

No paid BI platform, external dashboard SaaS, email delivery service, production AWS reporting resources, or recurring spend is authorized. Reports must operate from the existing application database in local/Docker deployments.

## Definition of done

- Report data is scoped to the authenticated tenant, with deliberate superuser behavior.
- Existing feature entitlements are not bypassed by reports.
- CSV schemas are deterministic and tested.
- Synchronous exports are bounded; larger/background execution is an explicit future extension.
- Report/export actions that expose operational or governance evidence are auditable.
- CI backend, frontend, and Docker checks pass.
- Documentation describes supported report families, filters, limits, and extension points.
