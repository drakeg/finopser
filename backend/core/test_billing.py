from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .account_models import OrganizationMembership, Subscription
from .models import CloudAccount, Organization


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

    def create_account(self, account_id: str, name: str):
        return CloudAccount.objects.create(
            provider=CloudAccount.Provider.AWS,
            organization=self.organization,
            name=name,
            provider_account_id=account_id,
            role_arn=f"arn:aws:iam::{account_id}:role/FinopserReadRole",
        )

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
        self.assertEqual(response.json()["effective_plan"], Subscription.Plan.FREE)
        self.assertEqual(response.json()["status"], Subscription.Status.FREE)
        self.assertEqual(response.json()["usage"]["cloud_accounts"], 0)
        self.assertFalse(response.json()["over_limit"])
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

    def test_downgrade_preserves_existing_accounts_and_reports_over_limit(self):
        self.subscription.plan = Subscription.Plan.BUSINESS
        self.subscription.status = Subscription.Status.ACTIVE
        self.subscription.save(update_fields=["plan", "status", "updated_at"])
        self.create_account("111111111111", "Account One")
        self.create_account("222222222222", "Account Two")

        self.subscription.status = Subscription.Status.CANCELED
        self.subscription.save(update_fields=["status", "updated_at"])

        response = self.client.get("/api/billing/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["plan"], Subscription.Plan.BUSINESS)
        self.assertEqual(response.json()["effective_plan"], Subscription.Plan.FREE)
        self.assertEqual(response.json()["max_cloud_accounts"], 1)
        self.assertEqual(response.json()["usage"]["cloud_accounts"], 2)
        self.assertEqual(response.json()["usage"]["cloud_accounts_over_limit"], 1)
        self.assertTrue(response.json()["over_limit"])
        self.assertEqual(CloudAccount.objects.filter(organization=self.organization).count(), 2)

    def test_over_limit_downgrade_blocks_new_accounts_without_deleting_existing(self):
        self.subscription.plan = Subscription.Plan.BUSINESS
        self.subscription.status = Subscription.Status.CANCELED
        self.subscription.save(update_fields=["plan", "status", "updated_at"])
        self.create_account("333333333333", "Existing One")
        self.create_account("444444444444", "Existing Two")

        response = self.client.post(
            "/api/cloud-accounts/",
            {
                "provider": "aws",
                "organization": self.organization.id,
                "name": "Blocked Third",
                "provider_account_id": "555555555555",
                "role_arn": "arn:aws:iam::555555555555:role/FinopserReadRole",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 402)
        self.assertEqual(CloudAccount.objects.filter(organization=self.organization).count(), 2)
