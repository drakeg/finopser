# Sprint 15 — Notifications and actionable alerts

## Goal

Turn existing governance, FinOps, billing, remediation, and operational signals into tenant-safe actionable notifications without requiring an external paid delivery service.

## Foundation slice

- Adds tenant-owned in-app notifications with severity, category, title/detail, action target, source object context, read/unread state, timestamps, occurrence counts, and deterministic deduplication keys.
- Enforces one notification per organization + deduplication key so repeated source events coalesce instead of creating notification storms.
- Repeated events refresh the notification, increment the occurrence count, and return it to unread state.
- Adds a provider-neutral delivery boundary. External delivery is disabled by default through `NOTIFICATION_PROVIDER=disabled` behavior and requires no credentials or recurring spend.
- Adds tenant-scoped APIs for listing/filtering notifications, unread count, mark read, mark unread, and mark all read.
- Superusers deliberately receive global notification visibility; ordinary users are restricted to their organization.
- Billing lifecycle events create in-app attention notifications for past-due and canceled subscriptions after trusted webhook processing.

## Governance signal slice

- Budget evaluation emits tenant-owned warning/high/critical notifications for the current active threshold level.
- Budget notifications deduplicate by organization, budget, period, and active level so repeated evaluation coalesces rather than creating new rows.
- Compliance evaluation emits one coalesced high-severity notification per tenant while failing checks remain present.
- Policy evaluation emits one coalesced high-severity notification per tenant while violations remain present.
- Governance notifications carry console targets (`Budgets`, `Compliance`, `Policies`) and source object metadata for the upcoming UI navigation layer.
- Regression tests cover source generation and repeated-event coalescing.

## API

- `GET /api/notifications/`
- `GET /api/notifications/unread-count/`
- `POST /api/notifications/<id>/read/`
- `POST /api/notifications/<id>/unread/`
- `POST /api/notifications/mark-all-read/`

List filters support `unread`, `category`, and `severity`.

## Safety and cost gate

No external notification SaaS, paid email provider, Slack activation, production webhook registration, or recurring spend is enabled. Local and Docker operation continues with external delivery disabled.

## Next slices

- Generate notifications from recommendations, remediation lifecycle, and inventory/cost sync failures through the notification service helper.
- Add operational-console notification bell/count, recent alerts, filtering, and navigation to relevant sections.
- Add audit coverage for notification state changes where appropriate.
- Add optional disabled-by-default external adapters after in-app behavior is stable.
