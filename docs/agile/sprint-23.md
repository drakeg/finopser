# Sprint 23 — Service Principals for Read-Only Automation

## Sprint goal

Continue E022 Public API / CLI / Integrations by separating non-human automation identity from interactive user identity while preserving the stable read-only `/api/v1/` contract.

## Issues

- #87 — Sprint 23: Service principals for read-only automation
- #88 — Sprint 23 slice 1: Establish service-principal identity model
- #90 — Sprint 23 slice 2: Service-principal lifecycle management
- #92 — Sprint 23 slice 3: Service-principal hardening and acceptance

## Slice 1 — Identity foundation

A service principal is a tenant-bound, non-human identity used only for machine authentication. It has its own active/disabled lifecycle and does not borrow the runtime identity of the human administrator who created it.

API credentials may reference a service principal. The existing `created_by` relationship remains as immutable human provenance for governance and audit purposes, but it is not the runtime authorization identity of a service-bound credential.

Bearer authentication keeps the Sprint 20–22 safety contract:

- only approved read-only scopes are recognized;
- only safe HTTP methods are accepted;
- `/api/v1/` remains the stable machine-consumer namespace;
- the service principal is scoped directly to its organization;
- disabling the service principal fails authentication closed;
- deactivating the original human creator does not disable an otherwise active service principal;
- existing human-owned API credentials remain backward compatible and still depend on their owner retaining workspace access.

## Slice 2 — Lifecycle management

Managers can manage tenant-scoped non-human identities through the existing session-authenticated integration boundary:

- `GET/POST /api/integrations/service-principals/` lists or creates principals;
- `GET /api/integrations/service-principals/<id>/` returns a principal and its credential metadata;
- `POST /api/integrations/service-principals/<id>/disable/` immediately blocks authentication;
- `POST /api/integrations/service-principals/<id>/enable/` restores otherwise-valid credentials.

Token creation accepts an optional `service_principal` id. The selected principal must be active and belong to the manager's organization. Credential responses expose principal identity metadata but never the stored digest or a previously issued plaintext secret.

Disabling a principal does not silently revoke or delete its credentials. Credential state is preserved for audit/history and the authentication layer fails closed while the principal is disabled. Re-enabling restores credentials that remain active, unexpired, and correctly scoped. Rotation is blocked while the principal is disabled.

Lifecycle create/disable/enable actions and service-bound credential changes use the existing audit boundary. Cross-tenant principal operations return not found rather than exposing another tenant's identity metadata.

## Slice 3 — Management UI and acceptance hardening

The Administration integration workspace now exposes service principals alongside API credentials. Managers can create a named principal with a purpose description, see active/disabled state, disable or re-enable it, and bind new read-only credentials to an active principal. Existing human-owned credential issuance remains available from the same form.

Service-bound credentials identify their principal in the token table. A disabled principal is visibly reflected in credential state and rotation is unavailable until the principal is re-enabled. Issuance and rotation continue to use the copy-once secret panel; once dismissed or the workspace state is cleared, plaintext is not recoverable from Finopser.

End-to-end acceptance coverage exercises the complete machine-identity lifecycle:

1. create a service principal;
2. issue a read-only credential bound to it;
3. authenticate through `/api/v1/`;
4. disable the principal and verify immediate rejection;
5. re-enable it and verify authentication is restored;
6. rotate the credential and verify the old secret is rejected while the replacement works;
7. revoke the replacement and verify final rejection.

The acceptance test also verifies that lifecycle and credential audit records carry service-principal identity where applicable while never recording either plaintext token. Focused lifecycle tests retain non-manager denial, tenant isolation, disabled-principal issuance/rotation denial, and backward compatibility for human-owned credentials.

## Sprint 23 acceptance gate

Sprint 23 is complete when slice #92 is merged with CI green. At that point the implementation provides tenant-bound non-human identities, manager-controlled lifecycle management, copy-once read-only credentials, fail-closed disable/revoke behavior, auditable lifecycle evidence, tenant isolation, management UI, and end-to-end acceptance coverage without expanding the authorized public API boundary.

## Safety / cost gate

No write/remediation API scopes, credential persistence in the CLI, paid gateway, hosted integration service, production public exposure, recurring spend, or live cloud provisioning is authorized.
