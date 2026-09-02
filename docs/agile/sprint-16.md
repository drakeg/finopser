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

## Completed slices

### Reporting foundation

- Added a provider-neutral report catalog and deterministic resource-inventory CSV export.
- Inventory reports use only persisted normalized resources, remain tenant-scoped, support bounded filters, and cap synchronous output at 5,000 rows.
- Report exports produce audit events without storing exported payloads.

### Financial / cost reporting

- Added a deterministic `cost-detail` CSV report sourced only from persisted `CostRecord` evidence.
- Cost exports are tenant-scoped through cloud-account ownership and support account, project, exact service, start-date, and end-date filters.
- Date filters accept ISO `YYYY-MM-DD`, reject invalid ranges, and retain the shared 5,000-row synchronous export cap.
- CSV columns are stable: usage date, account, provider account ID, project, service, region, amount, currency, and record update timestamp.
- Financial exports use the shared audited report-export path and never invoke AWS Cost Explorer or another provider at report time.

### Governance and audit reporting

- Added deterministic CSV report families for compliance findings, policy violations, and application audit events.
- Compliance and policy reports are hidden from the report catalog and denied at the endpoint when the tenant lacks the corresponding plan entitlement.
- Governance exports remain tenant-scoped through cloud-account ownership and support account, status, and severity filters.
- Audit exports are tenant-scoped through the audit event's direct organization ownership and support action/object-type filters.
- Audit report rows intentionally omit metadata payloads so exports do not broaden exposure of potentially sensitive audit context.

### Recommendation and remediation reporting

- Added deterministic recommendation and remediation-history CSV report families so the initial catalog covers the full persisted evidence scope from issue #57.
- Recommendation exports require the existing `recommendations` entitlement and are tenant-scoped through direct organization ownership.
- Remediation-history exports require `remediation_simulation` and are tenant-scoped through cloud-account organization ownership.
- Recommendation filters cover account, status, priority, and category; remediation filters cover account, status, and simulation/live mode.
- Recommendation evidence/detail payloads and remediation parameters, previews, provider results, and event metadata are intentionally excluded from CSV output.

### Reports workspace

- Replaced the static Reports placeholder with an interactive report workspace driven by `/api/reports/`.
- The workspace only presents report definitions returned by the entitlement-filtered backend catalog.
- Report cards expose resource inventory, cost detail, compliance findings, policy violations, recommendations, remediation history, and audit events when available to the current tenant.
- Filter controls map directly to the bounded backend query parameters for each report family.
- CSV download actions call the existing authenticated export endpoints, preserving tenant scoping, audit logging, deterministic schemas, and the shared 5,000-row synchronous cap.
- Generated timestamp, row count, and truncation state are returned with each export; the workspace also surfaces the synchronous limit and report description before download.
- Reports no longer appear as `Planned` in the console navigation once the workspace module is loaded.
- The current synchronous workspace intentionally does not add scheduled delivery or external report infrastructure; those remain explicit future extensions.

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
