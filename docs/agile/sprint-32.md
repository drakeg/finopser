# Sprint 32 — Multi-cloud Provider Foundation

## Sprint goal
Begin the deferred multi-cloud roadmap by making provider boundaries explicit and extensible before introducing any non-AWS SDK, credential flow, discovery call, or cloud mutation.

## Slice 1 — Provider contract and registry

- Replace the hard-coded AWS registry conditional with an explicit provider factory registry.
- Preserve existing AWS behavior and normalize provider lookup names.
- Add Azure to the CloudAccount provider vocabulary so tenant data can represent the future provider without claiming implementation support.
- Keep Azure lookup fail-closed until an Azure provider implementation is deliberately registered.
- Cover registry lookup, normalization, unsupported Azure, duplicate registration, and invalid registration with local unit tests.

## Safety / cost gate
No Azure/GCP/OCI SDK calls, credentials, resource discovery, cost retrieval, mutations, hosted infrastructure, paid services, or recurring spend are introduced in this slice.

## Tracking
- #162 — Sprint 32: Multi-cloud provider foundation
- #163 — Slice 1: Generalize provider contract and registry
