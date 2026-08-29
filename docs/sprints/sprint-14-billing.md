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

## Remaining Sprint 14 work

- Frontend upgrade/manage-subscription experience using the billing endpoints.
- Downgrade UX for organizations above lower-plan resource/member limits without deleting tenant data.
- Final billing lifecycle regression pass and issue #44 acceptance review.
