# Sprint 28 — Enterprise Identity Authentication Flows

## Sprint goal

Continue E017 Enterprise Identity from the Sprint 18 configuration/discovery foundation into safe, provider-neutral authentication flow mechanics while preserving local authentication as fallback.

## Issues

- #122 — Sprint 28: Enterprise identity authentication flows
- #123 — Sprint 28 slice 1: OIDC authorization request foundation

## Slice 1 — OIDC authorization request foundation

An enabled OIDC workspace can now start a local authorization request with `POST /api/auth/sso/oidc/authorize/` using an email address whose domain matches the existing tenant-owned enterprise identity configuration.

The request foundation:
- generates cryptographically random state, nonce, and PKCE verifier values;
- persists only callback-validation state on the server;
- stores a SHA-256 digest of state rather than the state value itself;
- binds the flow to the matching enterprise identity configuration/workspace;
- uses a ten-minute expiry and supports one-time consumption state for the callback slice;
- creates an S256 PKCE challenge;
- builds the authorization URL from the configured issuer and client id;
- includes no client secret, secret reference, password, or other provider credential in the response or URL;
- deletes expired, unconsumed flow records for the selected configuration before creating a new flow.

Disabled configurations, non-OIDC configurations, unknown domains, and incomplete OIDC configurations fail closed. The implementation performs no provider network call; automated tests use only local/fake issuer metadata.

The callback URL is reserved at `/api/auth/sso/oidc/callback/` for the next slice. Slice 1 does not exchange authorization codes, create sessions, link identities, or perform JIT provisioning.

## Security semantics

Local username/password authentication remains unchanged. Enterprise SSO remains optional and disabled unless explicitly configured by a workspace manager.

No OIDC client secret is stored in the flow table. Existing `secret_reference` configuration is not returned by the authorization endpoint and is not required for authorization-request construction.

## Safety / cost gate

No paid identity provider, production SSO activation, hosted authentication service, external directory provisioning, SCIM, production infrastructure, live provider calls from CI, or recurring spend is authorized.
