# Sprint 15 — Notifications and actionable alerts

Issue: #49

## Objective

Surface tenant-safe, actionable in-app notifications from existing governance, FinOps, billing, remediation, and operational signals without requiring external paid services.

## Foundation scope

- Tenant-owned notification records with deterministic deduplication.
- Read/unread lifecycle and unread counts.
- Tenant-scoped notification APIs with explicit superuser behavior.
- Provider-neutral external-delivery boundary, disabled by default.
- Initial source integration for billing past-due and canceled states.
- Regression coverage for isolation, deduplication, state changes, superuser scope, and disabled external delivery.

## Cost gate

No external SaaS delivery, paid provider activation, or recurring spend is authorized in this sprint.
