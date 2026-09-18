# Sprint 24 — External Integrations and Outbound Delivery

## Sprint goal

Continue E022 Public API / CLI / Integrations with a controlled, tenant-bound foundation for outbound integrations while preserving the read-only API, service-principal, tenant-isolation, secret-handling, and zero-cost boundaries established in Sprints 20–23.

## Issues

- #94 — Sprint 24: External integrations and outbound delivery
- #95 — Sprint 24 slice 1: Establish integration destination lifecycle

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
