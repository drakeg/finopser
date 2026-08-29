from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .account_models import OrganizationMembership, Subscription
from .models import Organization


@override_settings(BILLING_PROVIDER="disabled")
class BillingFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="billing-owner", password="test-password-long")
        self.organization = Organization.objects.create(name="Billing Workspace")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.subscription = Subscription.objects.create(organization=self.organization)
        self.client = APIClient()
        self.client.login(username="billing-owner", password="test-password-long")

    def test_plan_catalog_reports_billing_disabled(self):
        self.client.logout()
        response = self.client.get("/api/plans/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["billing_provider_configured"])

    def test_status_is_workspace_subscription_and_disabled(self):
        response = self.client.get("/api/billing/status/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["configured"])
        self.assertEqual(response.json()["plan"], Subscription.Plan.FREE)
        self.assertEqual(response.json()["status"], Subscription.Status.FREE)
        self.assertFalse(response.json()["can_manage"])

    def test_checkout_rejects_free_and_stays_disabled_for_paid_plan(self):
        free = self.client.post("/api/billing/checkout/", {"plan": "free"}, format="json")
        self.assertEqual(free.status_code, 400)

        paid = self.client.post("/api/billing/checkout/", {"plan": "pro"}, format="json")
        self.assertEqual(paid.status_code, 503)
        self.assertFalse(paid.json()["billing_provider_configured"])
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan, Subscription.Plan.FREE)
        self.assertEqual(self.subscription.status, Subscription.Status.FREE)

    def test_portal_stays_disabled_without_provider(self):
        response = self.client.post("/api/billing/portal/", {}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["billing_provider_configured"])

    def test_billing_status_does_not_expose_another_workspace(self):
        other = Organization.objects.create(name="Other Billing Workspace")
        Subscription.objects.create(
            organization=other,
            plan=Subscription.Plan.BUSINESS,
            status=Subscription.Status.ACTIVE,
            billing_provider="test",
            provider_customer_id="other-customer",
        )

        response = self.client.get("/api/billing/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["plan"], Subscription.Plan.FREE)
        self.assertIsNone(response.json()["provider"])
