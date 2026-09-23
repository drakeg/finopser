# Sprint 27 — External Notification Coverage and Producer Hardening

Parent: #115

## Slice 1 — Recommendation external notification events

Issue: #116

Sprint 27 extends the shared external-notification framework to durable open recommendations through the explicit `recommendation.open` event.

The stable source identity combines organization ownership with the recommendation source key. Only open, tenant-owned recommendations are eligible. Dismissed, resolved, unowned, disabled-channel, and unsubscribed cases fail closed.

The outbound payload is deliberately metadata-only: recommendation id, source type, category, priority, status, title, estimated monthly savings, and related account/project/resource ids. Raw evidence, arbitrary detail text, and action/remediation instructions are excluded.

Notification dispatch remains side-effect free with respect to remediation: producing an external recommendation notification never creates, approves, or executes a remediation action. Channel selection, active-state checks, deterministic delivery identity, duplicate suppression, signing, bounded delivery, tenant isolation, and sanitized audit evidence remain centralized in the shared dispatch layer.

## Safety / cost gate

Automated coverage uses transient test signing material and in-process fake transport only. No production outbound networking, paid provider, live cloud provisioning, recurring spend, automatic external delivery from CI, automatic remediation, or write/remediation public API scope is authorized.
