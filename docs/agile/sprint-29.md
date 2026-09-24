# Sprint 29 — AWS Account Vending Execution Boundary

## Sprint goal

Continue E018 from Sprint 19's request/approval/preview foundation into a durable, provider-neutral execution boundary while keeping live AWS account creation impossible by default.

## Issues

- #129 — Sprint 29: AWS account vending execution boundary
- #130 — Sprint 29 slice 1: Durable account provisioning plans

## Slice 1 — Durable provisioning plans

An approved tenant-owned account-vending request can now produce one durable provisioning plan under explicit manager action.

The plan snapshots:
- vending request identity;
- account name, email, and environment;
- organization-node and project placement;
- selected baseline profile and its deterministic intended actions.

Plan creation is idempotent through a one-to-one request relationship. Repeating the operation returns the existing plan rather than creating another intent record.

Plans are deliberately non-executable metadata. Every plan reports `provider: disabled` and `live_provisioning: false`. Creating or reading a plan performs no AWS/network/provider call, stores no AWS credentials, and does not change the vending request approval state.

Plan creation is manager-only and requires an approved request in the caller's workspace. Existing plans remain readable to authenticated members of that same workspace, consistent with existing account-vending request visibility. Cross-tenant access fails closed.

Plan creation is audited with only plan id and disabled/live-provisioning metadata.

## Safety / cost gate

No AWS Organizations/CreateAccount, Control Tower enrollment, live AWS mutation, paid service activation, production infrastructure, recurring spend, automatic execution, or provider credentials are authorized.


## Slice 2 — Controlled provisioning execution contract

Provisioning plans now have durable execution attempts that can be requested only by a workspace manager and only while the underlying vending request remains approved.

Execution is routed through a provider-adapter contract. The default adapter is deliberately disabled and raises a controlled failure without performing any network or cloud-provider operation. Automated acceptance tests inject an in-process fake adapter only.

Each explicit execution request creates an attempt with running, succeeded, or failed lifecycle state. A plan may have at most one running attempt at a time. There is no scheduler, automatic retry, or background provider execution.

Persisted results are intentionally provider-neutral and sanitized. Success records only an outcome, opaque reference, and message supplied by the adapter contract. Controlled/default failures record only a coarse outcome. Unexpected adapter exceptions are reduced to `provider_error`; exception text, raw provider responses, credentials, tokens, and secrets are not persisted.

Execution request and completion are audited using execution id, provider label, and final status only. Executions do not mutate the original request approval or provisioning-plan intent.

The default application remains incapable of AWS account creation because the installed adapter is disabled. Live AWS Organizations/CreateAccount or Control Tower integration remains outside the authorized boundary.


## Slice 3 — Administration UX and acceptance hardening

Administration now exposes the tenant's account-vending request lifecycle alongside provisioning-plan and execution-attempt state. The interface labels provisioning as disabled by default and states that the installed provider does not create an AWS account.

For approved requests, the UI exposes only explicit actions: create a durable plan, then request an execution attempt. Pending requests expose manager approval. There is no automatic execution or retry path. Backend authorization remains authoritative; non-manager attempts still fail closed even if a client constructs a request manually.

Plan presentation includes the disabled provider, live-provisioning flag, and deterministic baseline actions. Execution history presents only the sanitized status/provider/outcome metadata already exposed by the backend.

Acceptance coverage verifies that repeated execution requires separate explicit requests, each attempt receives its own durable identity, disabled-provider results contain no exception details, history cannot cross tenant boundaries, and execution attempts do not mutate the provisioning-plan intent or enable live provisioning.

## Sprint 29 acceptance

Sprint 29 now provides request approval, deterministic preview, durable provisioning intent, an explicit provider-adapter execution boundary, sanitized execution history, and an administration workflow. The default adapter remains disabled, so the application is still incapable of live AWS account creation.

Activating AWS Organizations/CreateAccount or Control Tower remains a separate future authorization decision and is not part of Sprint 29.
