from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from django.test import TestCase

from .account_models import OnboardingProfile, OrganizationMembership, Subscription
from .models import CloudAccount, CostSync, InventorySync, Organization, OrganizationNode, Project


class OnboardingAndSubscriptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="new-owner",
            email="owner@example.com",
            password="test-password-long",
        )
        OnboardingProfile.objects.create(user=self.user)
        self.client = APIClient()
        self.client.login(username="new-owner", password="test-password-long")

    def create_organization(self):
        response = self.client.post(
            "/api/onboarding/organization/",
            {"name": "Example Cloud"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return Organization.objects.get(name="Example Cloud")

    def create_account(self, organization, account_id="123456789012"):
        return CloudAccount.objects.create(
            provider=CloudAccount.Provider.AWS,
            organization=organization,
            project=Project.objects.filter(organization=organization).first(),
            name="Primary AWS",
            provider_account_id=account_id,
            role_arn=f"arn:aws:iam::{account_id}:role/FinopserReadRole",
        )

    def test_create_organization_seeds_workspace_and_free_plan(self):
        organization = self.create_organization()

        membership = OrganizationMembership.objects.get(user=self.user, organization=organization)
        subscription = Subscription.objects.get(organization=organization)
        profile = OnboardingProfile.objects.get(user=self.user)

        self.assertEqual(membership.role, OrganizationMembership.Role.OWNER)
        self.assertEqual(subscription.plan, Subscription.Plan.FREE)
        self.assertEqual(subscription.status, Subscription.Status.FREE)
        self.assertTrue(OrganizationNode.objects.filter(organization=organization, name="Root").exists())
        self.assertTrue(Project.objects.filter(organization=organization, name="Default").exists())
        self.assertEqual(profile.current_step, OnboardingProfile.Step.CLOUD_ACCOUNT)

    def test_free_plan_limits_cloud_accounts_to_one(self):
        organization = self.create_organization()
        self.create_account(organization)

        response = self.client.post(
            "/api/onboarding/cloud-account/",
            {
                "name": "Second AWS",
                "provider_account_id": "210987654321",
                "role_arn": "arn:aws:iam::210987654321:role/FinopserReadRole",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 402)
        self.assertTrue(response.json()["upgrade_required"])

    def test_bootstrap_requires_both_inventory_and_cost_sync_before_completion(self):
        organization = self.create_organization()
        account = self.create_account(organization)
        account.status = CloudAccount.Status.VALID
        account.last_validated_at = timezone.now()
        account.save(update_fields=["status", "last_validated_at", "updated_at"])

        inventory = InventorySync.objects.create(
            cloud_account=account,
            status=InventorySync.Status.SUCCESS,
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )
        response = self.client.get("/api/account/bootstrap/")
        self.assertEqual(response.json()["onboarding"]["current_step"], OnboardingProfile.Step.SYNC)

        CostSync.objects.create(
            cloud_account=account,
            start_date=timezone.localdate().replace(day=1),
            end_date=timezone.localdate(),
            status=CostSync.Status.SUCCESS,
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )
        response = self.client.get("/api/account/bootstrap/")
        self.assertFalse(response.json()["onboarding"]["required"])
        self.assertEqual(response.json()["onboarding"]["current_step"], OnboardingProfile.Step.COMPLETE)
        inventory.refresh_from_db()

    def test_free_plan_is_denied_paid_api_families(self):
        self.create_organization()

        for path in (
            "/api/budgets/",
            "/api/compliance/summary/",
            "/api/policies/summary/",
            "/api/recommendations/summary/",
            "/api/remediations/summary/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 402)
                self.assertTrue(response.json()["upgrade_required"])

    def test_pro_unlocks_analysis_but_not_live_remediation(self):
        organization = self.create_organization()
        subscription = Subscription.objects.get(organization=organization)
        subscription.plan = Subscription.Plan.PRO
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["plan", "status", "updated_at"])

        self.assertNotEqual(self.client.get("/api/budgets/").status_code, 402)
        self.assertNotEqual(self.client.get("/api/compliance/summary/").status_code, 402)
        self.assertNotEqual(self.client.get("/api/recommendations/summary/").status_code, 402)
        self.assertNotEqual(self.client.get("/api/remediations/summary/").status_code, 402)

        execute = self.client.post("/api/remediations/999999/execute/", {}, format="json")
        self.assertEqual(execute.status_code, 402)
        self.assertEqual(execute.json()["required_feature"], "remediation_live")

    def test_business_plan_passes_live_remediation_paywall(self):
        organization = self.create_organization()
        subscription = Subscription.objects.get(organization=organization)
        subscription.plan = Subscription.Plan.BUSINESS
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["plan", "status", "updated_at"])

        response = self.client.post("/api/remediations/999999/execute/", {}, format="json")
        self.assertNotEqual(response.status_code, 402)

    def test_plan_catalog_is_public_and_does_not_claim_billing_is_active(self):
        self.client.logout()
        response = self.client.get("/api/plans/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([plan["code"] for plan in response.json()["plans"]], ["free", "pro", "business"])
        self.assertFalse(response.json()["billing_provider_configured"])
