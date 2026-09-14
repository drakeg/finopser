# Sprint 23 — Service Principals for Read-Only Automation

## Sprint goal

Continue E022 Public API / CLI / Integrations by separating non-human automation identity from interactive user identity while preserving the stable read-only `/api/v1/` contract.

## Issues

- #87 — Sprint 23: Service principals for read-only automation
- #88 — Sprint 23 slice 1: Establish service-principal identity model

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

## Planned next slices

- Add manager-controlled service-principal lifecycle endpoints for create/list/inspect/disable.
- Issue and rotate copy-once credentials bound to a selected service principal.
- Add lifecycle audit events, UI management, documentation, and end-to-end acceptance coverage.

## Safety / cost gate

No write/remediation API scopes, credential persistence in the CLI, paid gateway, hosted integration service, production public exposure, recurring spend, or live cloud provisioning is authorized.