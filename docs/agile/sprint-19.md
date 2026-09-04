# Sprint 19 — AWS Account Vending Foundation

## Sprint goal

Begin E018 AWS Account Vending with a tenant-safe request, approval, and deterministic preview workflow while keeping all live AWS account creation impossible by default.

## Issue

- #71 — Sprint 19: AWS account vending foundation

## Initial slice — request, approval, and preview

- Add tenant-owned account-vending requests with explicit pending, approved, and rejected lifecycle states.
- Capture account name/email, environment, purpose, organizational placement, project placement, and a named baseline profile.
- Allow authenticated workspace members to submit requests.
- Require an owner/admin or existing cloud-manager role to approve or reject a pending request.
- Reject cross-workspace organization-node and project placement.
- Provide deterministic baseline profiles for standard, sandbox, and production intent.
- Expose a preview that reports intended actions and readiness while always reporting `live_provisioning: false` and provider `disabled`.
- Audit request, approval, rejection, and preview activity.
- Do not store AWS credentials or call AWS Organizations / Control Tower.

## Provider boundary

This slice intentionally has no live account-vending provider. Approval means the request is ready for a future explicitly authorized provisioning adapter; it does not create an AWS account. A later adapter can map the persisted request and baseline intent to AWS Organizations or Control Tower only after a separate safety/cost authorization gate.

## Safety / cost gate

No AWS account creation, Control Tower enrollment, paid service activation, production infrastructure, recurring spend, or live provider mutation is authorized.

## Definition of done for this slice

- Requests and placement are tenant scoped.
- Non-manager members may request accounts but cannot approve or reject them.
- Managers may approve or reject only pending requests in their own workspace.
- Preview is deterministic and cannot mutate a cloud provider.
- Privileged lifecycle actions and previews are auditable.
- Backend/frontend/Docker CI remains green.
