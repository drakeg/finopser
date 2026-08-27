# Security Model

## Security Objectives

finopser is a privileged cloud-management platform. Security is therefore a foundational product requirement rather than a later hardening exercise.

## Operating Modes

All cloud-changing capabilities follow one of three modes:

### OBSERVE

Read, inventory, evaluate, and report. No cloud resource changes are performed.

### RECOMMEND

Produce an evidence-backed proposed action, including impact and risk where practical. No cloud resource changes are performed.

### ENFORCE

Execute an explicitly authorized action within a defined scope and permission boundary.

The platform should default to the least-privileged mode available. A finding or recommendation must never silently become a destructive action.

## AWS Authentication

AWS integrations should use STS AssumeRole and appropriate trust relationships rather than stored long-lived IAM user access keys.

Where cross-account trust is used, external IDs should be supported where appropriate. AWS permissions must be scoped by capability and least privilege.

## Application Security Requirements

- Modern password hashing.
- Server-side authorization on every protected action.
- Deny-by-default RBAC.
- CSRF/XSS protections where applicable.
- Rate limiting for sensitive endpoints.
- Secret-safe structured logging.
- No credentials or secrets committed to the repository.
- `.env.example` contains placeholders only.
- Provider calls use explicit timeouts and bounded retry behavior.
- Privileged actions emit audit events.
- Containers run as non-root where practical.
- Dependencies and container images receive automated vulnerability scanning.
- Sensitive configuration must be replaceable by production secret stores without changing application semantics.

## Audit Requirements

At minimum, the platform should audit material changes to:

- users, groups, roles, and permissions;
- cloud accounts and provider configuration;
- organizational hierarchy;
- policies and policy assignments;
- budgets and thresholds;
- compliance exceptions;
- automation and remediation configuration;
- enforcement actions.

Audit records should capture actor, action, target, timestamp, result, and relevant correlation/request identifiers.

## Enforcement Safety Requirements

Before an ENFORCE capability is accepted into a Sprint, its story must define:

- exact scope;
- provider permissions;
- blast radius;
- idempotency expectations;
- dry-run/recommendation behavior where feasible;
- authorization controls;
- audit events;
- partial-failure handling;
- rollback or compensating action where feasible.

## Production Secrets Direction

Local development uses environment-based configuration with non-secret examples committed to the repository. AWS production deployment should be able to use services such as Secrets Manager and KMS without embedding AWS-specific secret retrieval throughout business logic.
