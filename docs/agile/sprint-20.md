# Sprint 20 — Public API and Integration Authentication Foundation

## Sprint goal

Start E022 Public API / CLI / Integrations with tenant-bound machine authentication that is safe for read-only automation and preserves the existing browser/session authentication path.

## Issue

- #73 — Sprint 20: Public API and integration authentication foundation

## Initial slice — API credentials and read-only Bearer authentication

- Add organization-owned API credentials with active/revoked lifecycle and last-used metadata.
- Generate high-entropy token material at issuance and return the plaintext token exactly once.
- Persist only a short lookup prefix and SHA-256 digest of the full token; the usable token is not recoverable from the database.
- Restrict token listing, creation, and revocation to workspace managers using session/basic authentication rather than API-token authentication.
- Audit token creation and revocation without recording the token secret or digest.
- Add Bearer-token authentication ahead of the existing session/basic DRF authenticators while preserving their behavior when no Bearer token is supplied.
- Reject API-token requests that use unsafe HTTP methods.
- Reject API-token requests to endpoints outside the explicit read-only allowlist.
- Require the issuing user to remain active and attached to the issuing workspace.
- Scope downstream data using the same tenant ownership rules already used by the application.

## Initial read-only API surface

Bearer tokens are accepted only for safe requests under these API prefixes:

- `/api/dashboard/`
- `/api/cloud-accounts/`
- `/api/resources/`
- `/api/costs/`
- `/api/compliance/findings/`
- `/api/policy-violations/`
- `/api/recommendations/`
- `/api/reports/`

This is intentionally narrower than the complete authenticated product API. Token authentication does not enable notification management, billing, identity configuration, account vending, remediation, policy evaluation, budget evaluation, recommendation generation, or other mutation/control-plane operations.

## Token administration

Managers use the existing authenticated application identity:

- `GET /api/integrations/tokens/` — list token metadata for the current workspace.
- `POST /api/integrations/tokens/` with `{ "name": "automation" }` — issue a token. The response contains the plaintext `token` exactly once.
- `POST /api/integrations/tokens/<id>/revoke/` — revoke a token immediately.

Listing never returns the plaintext token or stored digest.

## CLI / automation example

After a manager creates a token, a read-only request can use:

```bash
curl -H "Authorization: Bearer $FINOPSER_API_TOKEN" \
  http://localhost:8080/api/cloud-accounts/
```

For a LAN deployment, use the normal Finopser frontend/Nginx address (for example `http://10.0.0.11:8080`) rather than addressing the Django backend port directly.

## Security semantics

API tokens are bearer secrets and must be protected like passwords. HTTPS is required before exposing this mechanism outside a trusted local/testing network. Finopser does not log or persist the usable token, and revocation removes its ability to authenticate immediately.

The current credential is linked to the manager who issued it rather than introducing a separate service-principal user type. If that user is disabled or no longer belongs to the issuing workspace, the token stops authenticating. This preserves existing tenant-scoping invariants for the first slice.

SHA-256 is appropriate here because the token contains cryptographically random high-entropy material rather than a human-memorable password. Future human passwords must continue to use Django's password hashing framework rather than this credential mechanism.

## Future slices

- Explicit credential scopes rather than the initial fixed read-only allowlist.
- Expiration and rotation policies.
- Dedicated service principals independent of human manager accounts.
- Stable API versioning and compatibility policy.
- Packaged CLI using the public API contract.
- Webhook subscriptions and signed delivery.
- Terraform/provider or other automation integrations after the API surface is stable.
- Rate limiting and abuse controls appropriate to the deployment boundary.

## Safety / cost gate

No paid API gateway, hosted integration platform, webhook delivery SaaS, production public exposure, recurring spend, or privileged machine-action capability is activated by this Sprint.

## Definition of done for this slice

- Token plaintext is visible only in the creation response and is not persisted.
- Token administration is manager-only and tenant-scoped.
- Valid Bearer tokens authenticate approved read-only endpoints and cannot cross workspace boundaries.
- Unsafe methods and non-approved endpoints are rejected for API-token authentication.
- Revoked tokens stop authenticating immediately.
- Existing browser/session authentication remains functional.
- Creation and revocation are audited without token secrets.
- Backend/frontend/Docker CI remains green.
