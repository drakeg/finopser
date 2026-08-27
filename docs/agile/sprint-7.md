# Sprint 7 — Compliance MVP

## Goal

Introduce a first-class, evidence-backed compliance layer over persisted inventory while preserving the platform's OBSERVE-only safety model.

## Scope

- normalized compliance frameworks and controls
- deterministic manual compliance evaluation from persisted `CloudResource` data
- findings with severity, evidence, first/last seen timestamps, and lifecycle
- statuses: open, resolved, excepted
- scoped exceptions with reason, optional account/resource scope, and expiry
- compliance summary and filtered findings APIs
- Compliance frontend section plus dashboard posture summary
- audit events for evaluations and exception changes
- tests proving evaluation makes no AWS/network calls
- no new CI job, service, worker, scheduler, or frontend dependency

## Initial AWS baseline

1. `AWS-EC2-001` — EC2 instances should not have a public IPv4 address.
2. `AWS-RDS-001` — RDS instances should not be publicly accessible.
3. `AWS-RDS-002` — RDS storage should be encrypted.

The required evidence is persisted during normal inventory discovery from fields already returned by existing EC2/RDS discovery responses. Compliance evaluation itself never calls AWS.

## Evidence rules

A control may return pass, fail, or unknown. Missing evidence must be counted as unknown and must never be converted into an assumed pass or failure. A previously open finding is resolved only when later persisted evidence explicitly passes the control; unknown evidence does not resolve it.

## Exceptions

Exceptions are application governance records, not cloud mutations. An active, unexpired exception can apply globally to a control, to one cloud account, or to one resource. A failing resource covered by an exception remains visible as an `excepted` finding rather than disappearing.

## Acceptance criteria

1. Baseline framework and controls are seeded by migration.
2. Authorized users can manually evaluate persisted inventory.
3. Evaluation does not make provider, boto3, or network calls.
4. Failed checks create/update one durable finding per control/resource.
5. Passing checks resolve previous findings.
6. Missing evidence increments unknown and does not invent a result.
7. Active exceptions convert covered failures to excepted status.
8. Findings can be filtered by status, severity, account, and control.
9. Summary exposes framework/control/finding/exception/latest-run posture.
10. Dashboard and Compliance UI expose posture using existing lightweight frontend patterns.
11. Existing inventory behavior, API contracts, Docker topology, and CI job topology remain intact.

## Non-goals

- AWS Config, Security Hub, Inspector, or other paid/optional service activation
- scheduled compliance polling
- policy enforcement or guardrails (Sprint 8)
- budgets (Sprint 9)
- recommendations (Sprint 10)
- remediation/automation (Sprint 11)
- AWS production deployment
