# Sprint 26 — Notification Event Producers and Policy Integration

Parent: #108

## Slice 1 — Budget threshold external notification events

Issue: #109

Sprint 26 begins connecting real application event producers to the Sprint 25 external-notification dispatch foundation. The first producer maps an existing budget threshold snapshot to the supported `cost.threshold` event without changing existing in-app budget notifications.

The stable source identity is `budget:<budget-id>:<period>:<level>`, matching the durable budget-period-threshold semantics already used by in-app notifications. The external payload contains only budget identity/name, period, threshold level, utilization, actual/limit amounts, and currency. Signing material is never included.

The producer delegates channel selection, active-state checks, tenant isolation, deterministic delivery identity, duplicate suppression, bounded signed webhook delivery, and sanitized audit evidence to the Sprint 25 dispatch policy. Signing-secret resolution and transport remain injected dependencies. Automated tests use only a transient test signing value and in-process fake transport.

## Safety / cost gate

No paid notification provider, production outbound networking, recurring spend, live cloud provisioning, automatic external delivery from CI, or write/remediation public API scopes are authorized.


## Slice 2 — Governance finding external notification events

Issue: #111

Open, non-excepted compliance findings can now be mapped to the supported `governance.finding` event. The stable source identity is the durable compliance-finding id, so repeated dispatch attempts are coalesced by the shared Sprint 25 delivery policy.

The outbound payload intentionally excludes the finding's raw evidence JSON. It contains only finding id, control code/title, severity/status, resource provider id/type, and region. Resolved and excepted findings fail closed. Channel subscription, destination/channel active state, tenant isolation, signing, retry bounds, duplicate suppression, and sanitized audit evidence continue to be enforced by the shared dispatch layer.

Existing compliance evaluation and in-app notification behavior is unchanged. Automated coverage uses injected transient signing material and an in-process fake transport only.
