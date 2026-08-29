import hashlib
import hmac
import json
import time

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .account_models import BillingEvent, OrganizationMembership, Subscription
from .entitlements import entitlement_payload
from .models import Organization


@override_settings(
    BILLING_PROVIDER="stripe",
    STRIPE_SECRET_KEY="sk_test_finopser",
    STRIPE_WEBHOOK_SECRET="whsec_finopser",
    STRIPE_PRICE_PRO="price_test_pro",
    STRIPE_PRICE_BUSINESS="price_test_business",
)
class BillingLifecycleTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Billing Tenant A")
        self.subscription = Subscription.objects.create(organization=self.organization)
        self.user = User.objects.create_user(username="billing-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client = APIClient()

    def _event(self, event_id="evt_1", status="active", plan="pro"):
        return {
            "id": event_id,
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_1",
                    "customer": "cus_test_1",
                    "status": status,
                    "current_period_end": int(time.time()) + 3600,
                    "metadata": {
                        "organization_id": str(self.organization.id),
                        "plan": plan,
                    },
                }
            },
        }

    def _signature(self, body: bytes, timestamp=None):
        timestamp = timestamp or int(time.time())
        digest = hmac.new(
            b"whsec_finopser",
            str(timestamp).encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        return f"t={timestamp},v1={digest}"

    def _post_event(self, event):
        body = json.dumps(event, separators=(",", ":")).encode()
        return self.client.post(
            "/api/billing/webhooks/stripe/",
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=self._signature(body),
        )

    def test_signed_webhook_updates_subscription_and_is_idempotent(self):
        first = self._post_event(self._event())
        second = self._post_event(self._event())

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["processed"])
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["processed"])
        self.assertEqual(BillingEvent.objects.filter(event_id="evt_1").count(), 1)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan, Subscription.Plan.PRO)
        self.assertEqual(self.subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(self.subscription.billing_provider, "stripe")
        self.assertEqual(self.subscription.provider_customer_id, "cus_test_1")
        self.assertEqual(self.subscription.provider_subscription_id, "sub_test_1")

    def test_invalid_signature_does_not_mutate_subscription(self):
        body = json.dumps(self._event()).encode()
        response = self.client.post(
            "/api/billing/webhooks/stripe/",
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=invalid",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(BillingEvent.objects.exists())
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan, Subscription.Plan.FREE)
        self.assertEqual(self.subscription.status, Subscription.Status.FREE)

    def test_canceled_paid_subscription_falls_back_to_free_entitlements(self):
        self.subscription.plan = Subscription.Plan.BUSINESS
        self.subscription.status = Subscription.Status.CANCELED
        self.subscription.save(update_fields=["plan", "status", "updated_at"])

        payload = entitlement_payload(self.organization)

        self.assertEqual(payload["plan"], Subscription.Plan.BUSINESS)
        self.assertEqual(payload["effective_plan"], Subscription.Plan.FREE)
        self.assertEqual(payload["max_cloud_accounts"], 1)
        self.assertFalse(payload["features"]["budgets"])
        self.assertFalse(payload["features"]["remediation_live"])

    def test_past_due_subscription_keeps_features_during_dunning_grace(self):
        self.subscription.plan = Subscription.Plan.PRO
        self.subscription.status = Subscription.Status.PAST_DUE
        self.subscription.save(update_fields=["plan", "status", "updated_at"])

        payload = entitlement_payload(self.organization)

        self.assertEqual(payload["effective_plan"], Subscription.Plan.PRO)
        self.assertTrue(payload["features"]["budgets"])

    def test_webhook_cannot_change_another_tenant_without_signed_metadata(self):
        other = Organization.objects.create(name="Billing Tenant B")
        other_subscription = Subscription.objects.create(organization=other)

        response = self._post_event(self._event(event_id="evt_tenant_a", plan="business"))

        self.assertEqual(response.status_code, 200)
        other_subscription.refresh_from_db()
        self.assertEqual(other_subscription.plan, Subscription.Plan.FREE)
        self.assertEqual(other_subscription.status, Subscription.Status.FREE)
