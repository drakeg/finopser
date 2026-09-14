# Sprint 23 — Service Principals for Read-Only Automation

## Sprint goal

Continue E022 Public API / CLI / Integrations by separating non-human automation identity from interactive user identity while preserving the stable read-only `/api/v1/` contract.

## Issues

- #87 — Sprint 23: Service principals for read-only automation
- #88 — Sprint 23 slice 1: Establish service-principal identity model
- #90 — Sprint 23 slice 2: Service-principal lifecycle management

## Slice 1 — Identity foundation

A service principal is a tenant-bound, non-human identity used only for machine authentication. It has its own active/disabled lifecycle and does not borrow the runtime identity of the human administrator who created it.

API credentials may now reference a service principal. The existing `created_by` relationship remains as immutable human provenance for governance and audit purposes, but it is not the runtime authorization identity of a service-bound credential.

Bearer authentication keeps the Sprint 20–22 safety contract:

- only approved read-only scopes are recognized;
- only safe HTTP methods are accepted;
- `/api/v1/` remains the stable machine-consumer namespace;
- the service principal is scoped directly to its organization;
- disabling the service principal fails authentication closed;
- deactivating the original human creator does not disable an otherwise active service principal;
- existing human-owned API credentials remain backward compatible and still depend on their owner retaining workspace access.

## Slice 2 — Lifecycle management

Managers can now manage tenant-scoped non-human identities through the existing session-authenticated integration boundary:

- `GET/POST /api/integrations/service-principals/` lists or creates principals;
- `GET /api/integrations/service-principals/<id>/` returns a principal and its credential metadata;
- `POST /api/integrations/service-principals/<id>/disable/` immediately blocks authentication;
- `POST /api/integrations/service-principals/<id>/enable/` restores otherwise-valid credentials.

Token creation accepts an optional `service_principal` id. The selected principal must be active and belong to the manager's organization. Credential responses expose principal identity metadata but never the stored digest or a previously issued plaintext secret.

Disabling a principal does not silently revoke or delete its credentials. Credential state is preserved for audit/history and the authentication layer fails closed while the principal is disabled. Re-enabling restores credentials that remain active, unexpired, and correctly scoped. Rotation is blocked while the principal is disabled.

Lifecycle create/disable/enable actions and service-bound credential changes use the existing audit boundary. Cross-tenant principal operations return not found rather than exposing another tenant's identity metadata.

## Planned next slices

- Add the service-principal management UI to the integration workspace.
- Harden lifecycle audit/documentation and complete end-to-end Sprint 23 acceptance coverage.

## Safety / cost gate

No write/remediation API scopes, credential persistence in the CLI, paid gateway, hosted integration service, production public exposure, recurring spend, or live cloud provisioning is authorized.