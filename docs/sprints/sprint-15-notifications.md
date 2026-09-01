# Sprint 15 — Notifications and actionable alerts

## Goal

Turn existing governance, FinOps, billing, remediation, and operational signals into tenant-safe actionable notifications without requiring an external paid delivery service.

## Foundation slice

- Adds tenant-owned in-app notifications with severity, category, title/detail, action target, source object context, timestamps, occurrence counts, and deterministic deduplication keys.
- Enforces one notification per organization + deduplication key so repeated source events coalesce instead of creating notification storms.
- Read/unread state is stored per user through notification receipts; one teammate reading an alert never changes another teammate's unread state.
- Repeated events refresh the notification, increment the occurrence count, clear existing user receipts, and return the alert to unread state for all users who can see it.
- Adds a provider-neutral delivery boundary. External delivery is disabled by default through `NOTIFICATION_PROVIDER=disabled` behavior and requires no credentials or recurring spend.
- Adds tenant-scoped APIs for listing/filtering notifications, unread count, mark read, mark unread, and mark all read.
- Superusers deliberately receive global notification visibility, but their read receipts remain personal; ordinary users are restricted to their organization.
- Notification read/unread state changes are recorded in the audit trail.
- Billing lifecycle events create in-app attention notifications for past-due and canceled subscriptions after trusted webhook processing.

## Governance signal slice

- Budget evaluation emits tenant-owned warning/high/critical notifications for the current active threshold level.
- Budget notifications deduplicate by organization, budget, period, and active level so repeated evaluation coalesces rather than creating new rows.
- Compliance evaluation emits one coalesced high-severity notification per tenant while failing checks remain present.
- Policy evaluation emits one coalesced high-severity notification per tenant while violations remain present.
- Governance notifications carry console targets (`Budgets`, `Compliance`, `Policies`) and source object metadata for the upcoming UI navigation layer.
- Regression tests cover source generation and repeated-event coalescing.

## Recommendation signal slice

- Open recommendations emit tenant-owned in-app notifications through the shared notification service.
- Recommendation notifications use the stable recommendation source key for deduplication, so repeated generation refreshes the existing alert instead of creating a notification storm.
- Notification severity follows recommendation priority and the action target routes users to `Recommendations`.
- Source metadata includes the recommendation object identifier for upcoming console navigation.
- Regression coverage verifies repeated generation coalesces the notification and preserves actionable metadata.

## Operational sync signal slice

- Failed inventory and cost syncs emit critical operational notifications.
- Partial inventory and cost syncs emit high-severity operational notifications while preserving the provider error detail.
- Sync notifications deduplicate by organization/account/sync type/status so repeated provider failures coalesce instead of creating alert storms.
- Successful syncs do not generate noise.
- Inventory alerts target `Accounts`; cost alerts target `Costs`, with the affected cloud-account identifier included as action metadata.
- Regression coverage verifies failed/partial generation, deduplication, severity, actionable target metadata, and quiet successful syncs.

## Remediation lifecycle slice

- A completed remediation preview emits a warning notification that an administrator decision is required.
- Stale evidence emits a high-severity notification directing the operator back to `Automation` for a new preview and approval.
- Failed execution emits a critical notification with bounded provider error context.
- Successful execution emits an informational completion notification; simulation success explicitly states that no provider mutation occurred.
- Remediation notifications are tenant-owned, target `Automation`, carry the remediation action identifier, and deduplicate by action plus lifecycle state.
- Rejected actions stay quiet because they are deliberate operator decisions rather than conditions requiring additional attention.
- Regression coverage verifies approval-required, stale, failed, and successful notification behavior without weakening the existing preview/approval/execution safety gates.

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

- Add operational-console notification bell/count, recent alerts, filtering, and navigation to relevant sections.
- Add optional disabled-by-default external adapters after in-app behavior is stable.
