# Sprint 8 — Policies & Guardrails

## Goal
Turn persisted cloud and compliance evidence into reusable, scoped governance policies without crossing the OBSERVE/RECOMMEND safety boundary.

## Scope
- First-class policy definitions with severity, mode, enabled state, rule key, and optional organization/node/project/account scope.
- Deterministic evaluation against persisted `CloudResource` and compliance evidence only.
- Durable policy violations with evidence, first/last observed timestamps, and automatic resolution when evidence passes.
- Explicit `unknown` results when required evidence is missing; never infer a pass or violation.
- Built-in guardrails for public EC2 IPv4 exposure, public RDS accessibility, and unencrypted RDS storage.
- Policy summary, policy/violation/run APIs, filters, and a frontend Policies view.
- Operational dashboard policy posture.
- RBAC: authenticated users may read; Platform Administrator, Cloud Administrator, and Security/Compliance Engineer may change/evaluate policies.
- Audit policy mutations and evaluations.

## Policy modes
- `observe`: identify and report evidence-backed violations.
- `recommend`: identify and report violations as recommended governance actions.

Sprint 8 deliberately does **not** implement an `enforce` mode. A policy mode never causes a provider call or cloud mutation.

## Scoping
A policy may be global or narrowed by one of the existing hierarchy dimensions: organization, organization node, project, or cloud account. More-specific scope is evaluated only against matching persisted resources. The API validates that combined scope values belong to the same organizational hierarchy.

## Built-in guardrails
The initial guardrails reuse evidence already collected for Sprint 7:
1. EC2 instances should not have a public IPv4 address.
2. RDS instances should not be publicly accessible.
3. RDS storage should be encrypted.

No new AWS API family is required. Missing metadata produces `unknown`, not a guessed result.

## Safety boundary
Policy evaluation reads the database only. It must not invoke boto3, AWS APIs, Terraform, SCPs, IAM mutation, AWS Config deployment, EventBridge, or remediation code. Docker Compose startup remains cloud-call-free.

## Non-goals
- Automatic enforcement or remediation.
- AWS Organizations/SCP deployment.
- IAM or resource mutation.
- Scheduled provider polling.
- Budgets and financial governance (Sprint 9).
- Recommendation engine (Sprint 10).
- Automation/remediation (Sprint 11).
- Production AWS deployment or paid/recurring service activation.

## Acceptance criteria
- Policies can be listed, created, updated, disabled, scoped, and evaluated through authenticated APIs with RBAC.
- Evaluation produces deterministic violations from persisted evidence and no AWS/network calls.
- Passing evidence resolves an existing violation; missing evidence increments unknown without creating a false violation.
- Scope limits evaluation to matching resources.
- Policy summary and violations are visible in the web UI/dashboard.
- Important policy writes/evaluations are audited.
- Backend, frontend, and Docker CI remain green without adding a new CI job, service, heavy frontend dependency, or duplicate image build.
