# Sprint 21 — Scoped API Credentials and Rotation

## Sprint goal

Continue E022 Public API / CLI / Integrations by replacing the initial broad read-only credential behavior with explicit least-privilege scopes, then add expiration and safe rotation in subsequent slices.

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

## Security boundary

Scopes only narrow the existing Sprint 20 read-only API boundary. They cannot grant access to mutation endpoints, notification management, billing, identity configuration, account vending, remediation, or other control-plane operations.

Tenant binding, issuing-user membership checks, active/revoked lifecycle, one-time plaintext display, digest-only storage, and session-auth compatibility remain unchanged.

## Next slices

- Optional credential expiration and authentication-time expiry enforcement.
- Atomic rotation with one-time replacement secret display and immediate superseded-token invalidation.
- Administration UI scope selection, expiration, and rotation controls.
- CLI packaging after the public API credential contract is stable.

## Safety / cost gate

No privileged machine mutation/remediation, paid API gateway, hosted integration platform, production public exposure, recurring spend, or live cloud provisioning is activated by this Sprint.
