# Sprint 24 — External Integrations and Outbound Delivery

## Sprint goal

Continue E022 Public API / CLI / Integrations with a controlled, tenant-bound foundation for outbound integrations while preserving the read-only API, service-principal, tenant-isolation, secret-handling, and zero-cost boundaries established in Sprints 20–23.

## Issues

- #94 — Sprint 24: External integrations and outbound delivery
- #95 — Sprint 24 slice 1: Establish integration destination lifecycle
- #97 — Sprint 24 slice 2: Safe signed webhook delivery

## Slice 1 — Integration destination lifecycle

Managers can create and govern tenant-scoped outbound integration destinations through the session-authenticated administration API. The first supported destination type is `webhook`; no provider-specific or paid integration is enabled by this slice.

Endpoints:

- `GET|POST /api/integrations/destinations/`
- `GET /api/integrations/destinations/{id}/`
- `POST /api/integrations/destinations/{id}/disable/`
- `POST /api/integrations/destinations/{id}/enable/`

Creation returns generated signing material exactly once. Normal list/detail/lifecycle responses expose only a non-secret prefix. The stored value is a SHA-256 digest rather than the plaintext creation secret, and audit metadata never includes the plaintext secret.

Endpoint URLs are restricted to HTTP(S), require a host, and reject embedded usernames/passwords. Destination names are unique per tenant. Cross-tenant object access returns 404 and non-manager lifecycle access returns 403.

This slice deliberately performs no outbound HTTP delivery. Delivery signing, bounded retry state, sanitized delivery history, local test delivery, and administration UI acceptance remain subsequent Sprint 24 slices.

## Safety / cost gate

Sprint 24 remains local/GitHub-CI only. No write/remediation API scopes, external paid integration service, production public exposure, recurring spend, live cloud provisioning, or automatic external delivery from CI is authorized. Future delivery tests must use local/fake endpoints only.


## Slice 2 — Safe signed webhook delivery

The delivery core supports only the explicit `governance.finding` and `report.ready` event types. It creates a deterministic JSON envelope and HMAC-SHA256 signature using the copy-once destination signing secret supplied by the caller at delivery time.

Delivery is transport-injected: production networking is not wired by this slice, so tests use in-process fake transports only. Disabled destinations and unsupported event types fail before any transport invocation.

Each delivery records tenant, destination, event identity, status, bounded attempt count, response status, and sanitized error class/status. It never stores request bodies, signing secrets, signatures, authorization headers, or provider exception messages. Delivery retries are bounded to three attempts.

Administration UI, local manager-facing test delivery, and sanitized history inspection remain for the Sprint 24 acceptance slice.
