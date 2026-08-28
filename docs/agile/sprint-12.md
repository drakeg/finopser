# Sprint 12 — Guided Onboarding and Subscription Entitlements

## Goal

Turn self-service registration into a usable product journey and establish a server-enforced subscription model without activating a paid billing provider.

## Delivered scope

- Guided post-authentication onboarding before the normal console loads.
- Organization/workspace creation with owner membership, root node, and default project.
- AWS account connection using existing AssumeRole architecture.
- Explicit STS validation step.
- Initial inventory and current-month cost sync step.
- Durable onboarding progress and completion state.
- Free, Pro, and Business subscription plans.
- Server-side feature entitlements and cloud-account limits.
- HTTP 402 upgrade responses for paid API families.
- Locked/Upgrade navigation for unavailable paid capabilities.
- Local Django admin management of memberships/subscriptions/onboarding state.
- Legacy-install migration preserving existing administrator functionality.
- Core Free-tier organization isolation for organizations/projects/accounts/resources/costs/dashboard.

## Plan matrix

- **Free** — one AWS account, inventory, cost visibility.
- **Pro** — up to five AWS accounts plus budgets, compliance, policies, recommendations, and remediation simulation.
- **Business** — up to fifty AWS accounts plus Pro capabilities, multi-user entitlement, and approval-gated live allowlisted remediation.

Prices and billing-provider product IDs are intentionally not defined in this sprint.

## Safety and non-goals

- No Stripe/Paddle/Marketplace activation.
- No payment collection.
- No production AWS deployment.
- No long-lived AWS credentials.
- No relaxation of remediation approval/stale-evidence controls.
- A paid plan does not replace RBAC.
- An organization owner does not become a global Platform Administrator.

## Follow-up blocker

The advanced governance engines and their historical run models were built during the original single-tenant roadmap. Before public paid SaaS activation, compliance, policy, budget, recommendation, remediation, audit, and run-history queries/evaluators must be fully organization-scoped and covered by cross-tenant isolation tests.
