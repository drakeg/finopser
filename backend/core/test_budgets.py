from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .budgets import budget_snapshot, evaluate_budgets
from .models import Budget, BudgetAlert, CloudAccount, CostRecord, Organization, OrganizationNode, Project
from .rbac import AUDITOR, FINOPS_ANALYST


class BudgetGovernanceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="finops", password="password")
        Group.objects.get_or_create(name=FINOPS_ANALYST)[0].user_set.add(self.user)
        self.client.force_authenticate(self.user)
        self.org = Organization.objects.create(name="Budget Org")
        self.node = OrganizationNode.objects.create(organization=self.org, name="Platform")
        self.project = Project.objects.create(
            organization=self.org, node=self.node, name="Core"
        )
        self.account = CloudAccount.objects.create(
            organization=self.org,
            project=self.project,
            name="Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.budget = Budget.objects.create(
            name="Production monthly",
            amount=Decimal("1000.00"),
            warning_threshold=Decimal("80"),
            critical_threshold=Decimal("90"),
            organization=self.org,
            cloud_account=self.account,
            created_by=self.user,
        )

    def cost(self, amount, usage_date=date(2026, 8, 10), account=None, currency="USD"):
        account = account or self.account
        return CostRecord.objects.create(
            provider="aws",
            cloud_account=account,
            project=account.project,
            provider_account_id=account.provider_account_id,
            usage_date=usage_date,
            service="AmazonEC2",
            region="us-east-1",
            amount=Decimal(amount),
            currency=currency,
            updated_at=timezone.now(),
        )

    @patch("core.providers.aws.boto3.client")
    def test_snapshot_uses_persisted_costs_only(self, client_mock):
        self.cost("500.00")
        snapshot = budget_snapshot(self.budget, date(2026, 8, 20))
        self.assertEqual(snapshot["actual"], Decimal("500.00000000"))
        self.assertEqual(snapshot["remaining"], Decimal("500.00000000"))
        self.assertEqual(snapshot["utilization"], Decimal("50.0"))
        self.assertEqual(snapshot["forecast"], Decimal("775.00"))
        client_mock.assert_not_called()

    def test_scope_and_currency_are_not_mixed(self):
        other = CloudAccount.objects.create(
            organization=self.org,
            project=self.project,
            name="Other",
            provider_account_id="210987654321",
            role_arn="arn:aws:iam::210987654321:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.cost("100.00")
        self.cost("700.00", account=other)
        self.cost("900.00", currency="EUR", usage_date=date(2026, 8, 11))
        snapshot = budget_snapshot(self.budget, date(2026, 8, 20))
        self.assertEqual(snapshot["actual"], Decimal("100.00000000"))

    def test_threshold_alerts_open_resolve_and_reopen(self):
        cost = self.cost("950.00")
        evaluate_budgets(self.user, date(2026, 8, 20))
        self.assertEqual(
            BudgetAlert.objects.filter(status=BudgetAlert.Status.OPEN).count(), 2
        )
        self.assertTrue(
            BudgetAlert.objects.filter(level=BudgetAlert.Level.CRITICAL).exists()
        )
        cost.amount = Decimal("700.00")
        cost.save(update_fields=["amount"])
        evaluate_budgets(self.user, date(2026, 8, 20))
        self.assertEqual(
            BudgetAlert.objects.filter(status=BudgetAlert.Status.OPEN).count(), 0
        )
        cost.amount = Decimal("1100.00")
        cost.save(update_fields=["amount"])
        evaluate_budgets(self.user, date(2026, 8, 20))
        self.assertEqual(
            BudgetAlert.objects.filter(status=BudgetAlert.Status.OPEN).count(), 3
        )
        self.assertTrue(
            BudgetAlert.objects.filter(
                level=BudgetAlert.Level.EXCEEDED, status=BudgetAlert.Status.OPEN
            ).exists()
        )

    def test_no_data_has_unknown_forecast(self):
        snapshot = budget_snapshot(self.budget, date(2026, 8, 20))
        self.assertFalse(snapshot["has_data"])
        self.assertIsNone(snapshot["forecast"])
        self.assertEqual(snapshot["level"], "ok")

    def test_threshold_validation_and_rbac(self):
        response = self.client.post(
            "/api/budgets/",
            {
                "name": "Invalid",
                "amount": "1000.00",
                "warning_threshold": "95",
                "critical_threshold": "90",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        auditor = User.objects.create_user(username="auditor-budget", password="password")
        Group.objects.get_or_create(name=AUDITOR)[0].user_set.add(auditor)
        self.client.force_authenticate(auditor)
        self.assertEqual(self.client.post("/api/budgets/evaluate/").status_code, 403)
        self.assertEqual(self.client.get("/api/budgets/summary/").status_code, 200)
