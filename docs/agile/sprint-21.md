# Sprint 21 — Scoped API Credentials and Rotation

## Sprint goal

Continue E022 Public API / CLI / Integrations by replacing the initial broad read-only credential behavior with explicit least-privilege scopes, optional expiration, and safe rotation.

## Issue

- #76 — Sprint 21: Scoped API credentials and rotation

## Slice 1 — Explicit read-only credential scopes

API credentials now carry an explicit list of read-only scopes. Authentication maps each approved public API prefix to one required scope and rejects a valid credential when that scope was not granted.

Supported scopes:

- `dashboard:read`
- `accounts:read`
- `resources:read`
- `costs:read`
- `compliance:read`
- `policies:read`
- `recommendations:read`
- `reports:read`

Token issuance accepts a non-empty `scopes` list. Unknown scopes, empty lists, and write-style scopes are rejected. Omitting `scopes` defaults to `accounts:read`, keeping newly issued credentials useful while making least privilege the default.

Existing Sprint 20 credentials are migrated to `accounts:read`; the migration does not broaden machine access.

Token listing and audit metadata include scope names but never the token secret or stored digest.

## Slice 2 — Optional credential expiration

Managers may optionally provide `expires_at` when issuing an API credential. Expiration must be a future ISO 8601 date-time with an explicit timezone. Omitting it preserves a non-expiring credential for integrations that require manual lifecycle management.

Authentication rejects expired credentials before scope authorization or `last_used_at` updates. Expiration is returned as safe credential metadata and included in the creation audit event, but token secrets and digests remain excluded.

Existing credentials remain non-expiring because the migration adds a nullable expiration field without changing their active state.

## Slice 3 — Atomic credential rotation

Managers may rotate a tenant-owned active API credential with `POST /api/integrations/tokens/<id>/rotate/`. Rotation replaces the credential's token prefix and digest inside a database transaction, returns the replacement plaintext exactly once, resets `last_used_at`, and immediately invalidates the superseded secret.

Scopes are preserved during rotation. Expiration is also preserved unless the manager explicitly supplies `expires_at`; an explicit blank value clears expiration, while a replacement date-time must pass the same future/timezone validation used during issuance. This allows an expired credential to be safely renewed without granting broader API access.

The rotation audit event records the credential name, previous and replacement token prefixes, scopes, and resulting expiration. It never records the plaintext token or digest. If audit recording or the credential update fails, the database transaction rolls back so the previous secret remains valid instead of leaving the integration in a partially rotated state.

Revoked credentials cannot be rotated. Tenant isolation and manager RBAC are enforced before credential mutation.

## Security boundary

Scopes, expiration, and rotation only operate within the existing Sprint 20 read-only API boundary. They cannot grant access to mutation endpoints, notification management, billing, identity configuration, account vending, remediation, or other control-plane operations.

Tenant binding, issuing-user membership checks, active/revoked lifecycle, one-time plaintext display, digest-only storage, and session-auth compatibility remain unchanged.

## Next slices

- Administration UI scope selection, expiration, and rotation controls.
- CLI packaging after the public API credential contract is stable.

## Safety / cost gate

No privileged machine mutation/remediation, paid API gateway, hosted integration platform, production public exposure, recurring spend, or live cloud provisioning is activated by this Sprint.
