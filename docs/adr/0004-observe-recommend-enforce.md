# ADR-0004 — Observe, Recommend, Enforce safety model

**Status:** Accepted

## Context

A cloud governance platform can eventually perform actions with significant financial, availability, and security impact. Safe adoption requires value before granting mutation permissions and explicit separation between detection and execution.

## Decision

All cloud-changing capabilities are classified as OBSERVE, RECOMMEND, or ENFORCE. The platform defaults to the least-privileged useful mode. Findings and recommendations do not automatically become enforcement actions.

## Consequences

- Read-only deployments remain useful.
- Enforcement stories require explicit authorization, permissions, scope, audit, failure handling, and blast-radius analysis.
- UI and APIs must make operating mode clear.
- Remediation architecture must preserve evidence linking observations, recommendations, approvals, and execution.
