# Sprint 18 — Enterprise Identity Foundation

## Sprint goal

Begin E017 Enterprise Identity with tenant-owned, provider-neutral SSO configuration and safe discovery while preserving Finopser's existing local authentication as the default and fallback.

## Issue

- #69 — Sprint 18: Enterprise identity foundation

## Initial slice — configuration and discovery

- Add one enterprise identity configuration per organization.
- Keep enterprise identity disabled by default.
- Support provider metadata for OpenID Connect and SAML 2.0 without implementing live authentication yet.
- Store only non-secret provider metadata in application records; credentials remain external and are represented only by an optional secret reference.
- Expose authenticated `GET/PUT /api/enterprise-identity/` configuration for the current workspace.
- Restrict configuration changes to existing manager roles while allowing authenticated workspace members to inspect status.
- Expose public `POST /api/auth/sso/discover/` email-domain discovery that returns only whether SSO is available and the provider type.
- Normalize domains case-insensitively and prevent one domain from being assigned to multiple workspaces.
- Audit privileged configuration changes without recording provider credentials.
- Preserve username/password login behavior.

## Security semantics

The discovery endpoint intentionally does not return organization names, tenant IDs, issuer URLs, client IDs, metadata URLs, entity IDs, or secret references. It only indicates whether an enabled enterprise identity configuration matches the submitted email domain and, if so, whether the provider type is OIDC or SAML.

The database does not contain OIDC client secrets, SAML private keys, or IdP signing credentials. A future provider adapter may resolve `secret_reference` through environment/configuration or another explicitly authorized secret backend.

## Future slices

- OIDC authorization-code flow with state/nonce/PKCE and callback validation.
- SAML authentication behind the same provider-neutral boundary.
- Workspace login UX and SSO redirect handling.
- Identity linking, group-to-role mapping, controlled JIT provisioning, and break-glass local access.
- SCIM or other lifecycle provisioning only after explicit design and authorization.

## Safety / cost gate

No paid identity provider, production SSO activation, hosted authentication service, external directory provisioning, production infrastructure, or recurring spend is authorized.

## Definition of done for this slice

- Enterprise identity configuration is explicitly tenant-owned and disabled by default.
- Only workspace managers can mutate identity configuration.
- Public discovery leaks no tenant identity or secret/configuration details beyond provider availability.
- Email domains cannot be claimed by multiple workspaces.
- Local password authentication remains functional.
- Configuration mutations are audited.
- Backend/frontend/Docker CI remains green.
