# Sprint 25 — External Notification Channels

## Sprint goal

Advance E014 Notifications and E022 Integrations by layering tenant-controlled external notification subscriptions on the Sprint 24 webhook destination and delivery foundation without enabling production outbound networking or paid services.

## Issues

- #101 — Sprint 25: External notification channels
- #102 — Sprint 25 slice 1: Notification channel lifecycle
- #104 — Sprint 25 slice 2: Notification dispatch policy and deduplication
- #106 — Sprint 25 slice 3: Notification administration and acceptance

## Slice 1 — Notification channel lifecycle

Managers can create tenant-bound notification channels that reference an existing active webhook destination. Channels select only from the explicit event catalog: `cost.threshold`, `governance.finding`, and `report.ready`.

Endpoints:

- `GET|POST /api/notification-channels/`
- `GET /api/notification-channels/{id}/`
- `POST /api/notification-channels/{id}/disable/`
- `POST /api/notification-channels/{id}/enable/`

Creation requires an active same-tenant destination and at least one supported event. Channel names are unique per tenant. Cross-tenant objects are hidden, non-manager management is denied, and a channel cannot be re-enabled while its destination is disabled. Channel responses and lifecycle audit evidence never contain signing secrets.

## Safety / cost gate

Sprint 25 remains local/GitHub-CI only. Slice 1 performs no outbound network delivery. No paid notification provider, production public exposure, recurring spend, live cloud provisioning, automatic external delivery from CI, or write/remediation public API scopes are authorized.


## Slice 2 — Dispatch policy and deduplication

The dispatch policy resolves only active same-tenant channels whose active destination is subscribed to the requested event. Supported events remain `cost.threshold`, `governance.finding`, and `report.ready`. Unknown events fail before delivery.

Each channel/source/event tuple receives a deterministic SHA-256 event id. An existing delivery with that tenant, destination, and event id is reused instead of invoking transport again, bounding duplicate dispatch. New delivery delegates to the Sprint 24 signed webhook core, retaining its three-attempt maximum and sanitized delivery history.

Signing-secret lookup and transport remain dependency-injected. No production network transport or persistent recoverable signing secret is introduced. Dispatch audit metadata contains delivery/event/status identifiers only and never includes secrets, signatures, request bodies, authorization headers, or provider diagnostics.


## Slice 3 — Administration and acceptance

The Administration workspace now manages external notification channels alongside webhook destinations and automation identities. Managers can select an active destination, subscribe a channel to the explicit event catalog, disable/re-enable channels, exercise an in-process local test, and inspect sanitized delivery evidence.

The test endpoint invokes the Sprint 25 dispatch policy with an injected fake 204 transport and a transient test-only signing value; it never contacts the configured webhook URL. Stable source ids exercise deterministic duplicate suppression. Disabled channels or destinations reject test execution, cross-tenant resources remain hidden, and non-manager access is denied.

Sprint 25 acceptance covers channel lifecycle, event subscription, dispatch selection, bounded signed-delivery reuse, duplicate suppression, sanitized history/audit evidence, manager UI, and local/fake end-to-end testing while retaining the zero-cost/no-production-network boundary.
