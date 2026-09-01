# Sprint 14 — SaaS billing and subscription lifecycle

## Goal

Add a production-shaped but disabled-by-default billing lifecycle on top of the existing subscription entitlement model without weakening local/self-hosted operation.

## Slice 1 — Billing foundation

- Provider-neutral billing boundary.
- Billing disabled by default.
- Authenticated billing status, checkout, and portal endpoints.
- Safe failure when no provider is configured.

## Slice 2 — Stripe test-mode lifecycle

- Stripe adapter uses the HTTPS API without adding a new runtime package.
- Adapter accepts only `sk_test_` credentials; live Stripe secret keys remain blocked by design.
- Checkout attaches organization and requested-plan metadata to both the Checkout Session and resulting subscription.
- Billing portal requires an existing provider customer id.
- Public webhook endpoint verifies Stripe-style timestamped HMAC signatures with a five-minute tolerance.
- Webhook processing is idempotent through the `BillingEvent` provider/event-id uniqueness constraint.
- Subscription create/update/delete events map Stripe lifecycle state into the existing `Subscription` model.
- Signed subscription metadata is used to locate the owning organization; invalid or missing organization/plan metadata is rejected transactionally.
- New billing state changes create tenant-owned audit events without recording secrets or payment details.
- Canceled/unpaid subscriptions retain their selected plan for history/display but receive Free entitlements through `effective_plan`.
- Trialing, active, and past-due subscriptions keep paid entitlements. Past-due is an explicit dunning grace policy for now.

## Slice 3 — Downgrade and over-limit behavior

- A downgrade or cancellation never deletes cloud accounts or other tenant data.
- Subscription and billing-status payloads expose the selected plan, effective plan, current cloud-account usage, effective account limit, and over-limit state.
- Existing cloud accounts remain readable and manageable after a downgrade, including when usage exceeds the lower plan limit.
- New cloud-account creation remains blocked while current usage is at or above the effective plan limit.
- Paid feature families are governed by the effective plan, so canceled/unpaid subscriptions cannot continue using paid governance features even though their data remains stored.
- This policy intentionally favors data preservation over destructive automatic cleanup. A tenant can reduce usage manually or restore a qualifying paid plan.

## Slice 4 — Billing management UX

- Authenticated console users get a Billing launcher that shows selected plan, effective plan, subscription status, cloud-account usage, and effective limit.
- The billing panel renders the public Free/Pro/Business plan catalog and identifies the current selection.
- Upgrade actions call the existing checkout endpoint only when billing is configured; disabled deployments show an explicit non-destructive billing-disabled message instead of a dead control.
- Existing provider customers can open the configured provider billing portal from the same panel.
- Over-limit workspaces receive a visible warning explaining that existing data is preserved while additional account creation stays blocked.
- Payment details remain provider-hosted and are not collected or stored by the Finopser frontend.
- Guided onboarding continues to show plan capabilities but defers paid-plan management until setup is complete.

## Local configuration

Billing remains disabled unless explicitly enabled:

```text
BILLING_PROVIDER=disabled
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_PRO=
STRIPE_PRICE_BUSINESS=
```

For isolated test-mode integration, set `BILLING_PROVIDER=stripe` and use only Stripe test-mode values. The application rejects a secret key that does not begin with `sk_test_`.

Webhook endpoint:

```text
/api/billing/webhooks/stripe/
```

## Safety gate

No live provider activation, production webhook registration, plan purchase, or recurring spend is authorized by this sprint. Live Stripe keys are intentionally rejected. Production activation requires a separate explicit authorization and review.

## Sprint 14 acceptance review

The implementation now covers the issue #44 acceptance path in automated/backend-enforced form: Free subscriptions exist without payment details; paid-plan checkout is available through a provider-neutral boundary; signed/idempotent provider events are the trusted path for subscription state changes; entitlements follow effective subscription state; cancellation/downgrade preserves tenant data while enforcing lower limits; billing data stays organization-scoped; and the application remains fully usable with billing disabled.

Production billing activation remains intentionally outside Sprint 14 and still requires separate authorization.
