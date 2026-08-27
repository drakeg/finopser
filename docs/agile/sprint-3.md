# Sprint 3 — AWS Account Onboarding

## Goal

Introduce the first provider integration without changing finopser's OBSERVE-only safety boundary.

## Scope

- provider abstraction and registry
- AWS adapter using STS AssumeRole
- cloud account persistence and organization/project assignment
- explicit connection validation
- validation/audit state
- Accounts UI guidance
- mocked provider tests
- AWS onboarding documentation

## Acceptance gate

A permitted administrator can register an AWS account using an account ID and role ARN, explicitly validate access through STS, and receive a persisted safe validation state. Docker must still start and function without any AWS credentials or network access. Long-lived AWS access keys are not supported or stored.

## Non-goals

AWS Organizations discovery, resource inventory, cost ingestion, compliance checks, remediation, account vending, and AWS deployment are deferred.

Tracker: #9
