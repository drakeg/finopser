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

## Slice 2 — Provider-neutral connection contract

The shared provider protocol now accepts a `ProviderConnection` containing a provider account identifier and opaque provider-specific authentication values. Existing AWS account records remain unchanged; validation, inventory, and cost call sites adapt the stored role ARN/external ID into the neutral contract at the provider boundary. AWS behavior is regression-tested through injected mocks and no live provider network calls are added.

## Slice 3 — Injected Azure provider boundary

An Azure provider now implements the normalized validation, inventory, and cost contracts through an injected adapter protocol. It normalizes subscription identity, Azure resource records, and cost records into the existing provider-neutral result types and sanitizes adapter failures before exposing them to callers. The default provider registry intentionally does not register Azure yet, so no Azure network behavior can occur without a future explicit runtime adapter/configuration slice.
