# AWS Cost Ingestion

Sprint 5 adds explicit, read-only AWS Cost Explorer ingestion. Cost sync is never automatic during local startup or CI.

## Operational cost note

AWS Cost Explorer API requests can incur AWS charges. Finopser does not enable a paid service or make live Cost Explorer calls automatically. Administrators choose when to run a cost sync and should review current AWS Cost Explorer pricing before production use.

## Permissions

The assumed role used for a cloud account needs `ce:GetCostAndUsage` for Sprint 5 cost ingestion. Keep this permission separate from inventory permissions and grant only what is required.

Example identity-policy statement:

```json
{
  "Effect": "Allow",
  "Action": ["ce:GetCostAndUsage"],
  "Resource": "*"
}
```

## Sync API

POST `/api/cloud-accounts/<id>/sync-costs/` with:

```json
{"start_date": "2026-08-01", "end_date": "2026-08-27"}
```

The end date is exclusive, matching AWS Cost Explorer semantics. A single request is limited to 366 days.

Normalized data is available from `/api/costs/`. Summary data is available at `/api/costs/summary/`, and filtered CSV export at `/api/costs/export/` using the same query parameters as the list endpoint.

Supported filters are cloud account, service, region, project, currency, start date, and end date. Re-running a date range updates existing normalized dimensions instead of creating duplicate rows.
