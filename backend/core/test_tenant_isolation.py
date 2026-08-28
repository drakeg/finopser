from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .account_models import OrganizationMembership, Subscription
from .models import Budget, CloudAccount, Organization, OrganizationNode, Project


class PaidFeatureTenantIsolationTests(APITestCase):
    def _workspace(self, suffix):
        user = User.objects.create_user(username=f"owner-{suffix}", password="password")
        organization = Organization.objects.create(name=f"Tenant {suffix}")
        node = OrganizationNode.objects.create(organization=organization, name="Root")
        project = Project.objects.create(organization=organization, node=node, name="Default")
        account = CloudAccount.objects.create(
            organization=organization,
            project=project,
            name=f"Account {suffix}",
            provider_account_id=f"{int(suffix):012d}",
            role_arn=f"arn:aws:iam::{int(suffix):012d}:role/FinopserReadOnly",
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        Subscription.objects.create(
            organization=organization,
            plan=Subscription.Plan.PRO,
            status=Subscription.Status.ACTIVE,
        )
        return user, organization, node, project, account

    def setUp(self):
        self.user_a, self.org_a, self.node_a, self.project_a, self.account_a = self._workspace("101")
        self.user_b, self.org_b, self.node_b, self.project_b, self.account_b = self._workspace("202")
        self.budget_a = Budget.objects.create(
            name="A budget",
            amount=Decimal("100.00"),
            organization=self.org_a,
            cloud_account=self.account_a,
            created_by=self.user_a,
        )
        self.budget_b = Budget.objects.create(
            name="B budget",
            amount=Decimal("200.00"),
            organization=self.org_b,
            cloud_account=self.account_b,
            created_by=self.user_b,
        )
        self.client.force_authenticate(self.user_a)

    def test_budget_list_retrieve_and_summary_do_not_leak_other_workspace(self):
        response = self.client.get("/api/budgets/")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.budget_a.id})
        self.assertEqual(self.client.get(f"/api/budgets/{self.budget_b.id}/").status_code, 404)
        summary = self.client.get("/api/budgets/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["budgets"]["total"], 1)
        self.assertEqual(summary.data["budgets"]["amount"], Decimal("100.00"))

    def test_budget_create_cannot_reference_other_workspace_objects(self):
        response = self.client.post(
            "/api/budgets/",
            {
                "name": "Cross tenant",
                "amount": "100.00",
                "organization": self.org_b.id,
                "cloud_account": self.account_b.id,
            },
            format="json",
        )
        self.assertIn(response.status_code, {400, 403})
        self.assertFalse(Budget.objects.filter(name="Cross tenant").exists())
