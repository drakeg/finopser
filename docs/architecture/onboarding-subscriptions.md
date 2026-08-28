# Onboarding and Subscription Entitlements

## Purpose

Finopser now separates three concerns that must not be conflated:

1. **Authentication** — who the user is.
2. **Organization/RBAC** — what the user may do inside a workspace.
3. **Subscription entitlements** — which product capabilities the workspace has purchased.

A powerful role does not bypass the subscription paywall, and a paid plan does not grant administrative permissions by itself.

## Guided onboarding

After registration or sign-in, the frontend checks `/api/account/bootstrap/` before loading the normal console. New users are guided through:

1. **Create organization** — establishes the workspace boundary, a root organization node, a default project, an owner membership, and a Free subscription.
2. **Connect AWS account** — stores account metadata, AssumeRole ARN, and optional External ID. Long-lived AWS access keys are not collected or stored.
3. **Validate connection** — uses the existing provider validation path based on STS AssumeRole and GetCallerIdentity.
4. **Initial sync** — runs resource inventory and current-month cost collection. Onboarding completes only when both have a successful or partial-success result.

Existing installations are grandfathered by migration into a completed onboarding state and a legacy Business subscription so the new productization layer does not remove existing administrator functionality.

## Plans

Prices are intentionally not defined in code yet. No external billing provider is activated by this sprint.

| Capability | Free | Pro | Business |
| --- | --- | --- | --- |
| AWS accounts | 1 | Up to 5 | Up to 50 |
| Inventory | Yes | Yes | Yes |
| Cost visibility | Yes | Yes | Yes |
| Budgets and forecasts | No | Yes | Yes |
| Compliance | No | Yes | Yes |
| Policies | No | Yes | Yes |
| Recommendations | No | Yes | Yes |
| Remediation simulation | No | Yes | Yes |
| Live allowlisted remediation | No | No | Yes |
| Multi-user product entitlement | No | No | Yes |

The current plan is stored on `Subscription`, one per organization. Future payment integration should update this durable subscription state rather than embedding payment-provider logic throughout product APIs.

## Paywall enforcement

The frontend marks plan-gated navigation as **Upgrade**, but the UI is not the security boundary.

`SubscriptionEntitlementMiddleware` enforces paid API families on the server and returns HTTP `402` with:

```json
{
  "detail": "Your current subscription does not include this feature.",
  "upgrade_required": true,
  "required_feature": "compliance"
}
```

The cloud-account onboarding endpoint also enforces the account limit for the current plan.

Superusers retain platform-level access for local administration and migration compatibility. Organization owners do not automatically become global Platform Administrators.

## Tenant boundaries

This sprint scopes the core Free-tier data surfaces to the authenticated user's organization:

- organizations, nodes, and projects
- cloud accounts
- resource inventory
- inventory sync history
- costs and cost sync history
- operational dashboard

Audit visibility for non-superusers is restricted to events performed by that user until audit records gain an explicit organization key.

The advanced governance engines were originally implemented as single-tenant/global evaluators. Full organization scoping of compliance, policies, budgets, recommendations, remediation history, run history, and audit history is a blocker before enabling a public payment provider or treating the product as production multi-tenant SaaS.

## Billing integration boundary

No Stripe, Paddle, AWS Marketplace, or other paid billing service is activated here. A later billing integration should be responsible for:

- checkout/customer portal
- webhook verification
- trial/active/past-due/canceled transitions
- mapping products/prices to `free`, `pro`, or `business`
- updating provider customer/subscription identifiers and current period end

Product APIs should continue to depend on Finopser's internal entitlement model rather than querying a billing provider during normal requests.
