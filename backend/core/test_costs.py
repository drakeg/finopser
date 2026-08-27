from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import CloudAccount, CostRecord, Organization, OrganizationNode, Project
from .providers.aws_costs import fetch_aws_costs
from .providers.base import CostRecord as ProviderCostRecord
from .providers.base import CostResult
from .rbac import PLATFORM_ADMIN


class AWSCostProviderTests(APITestCase):
    def test_cost_explorer_response_is_normalized(self):
        provider = MagicMock()
        provider.config = object()
        provider._error_code.side_effect = lambda exc: exc.__class__.__name__
        session = MagicMock()
        client = MagicMock()
        provider._assumed_session.return_value = session
        session.client.return_value = client
        client.get_cost_and_usage.return_value = {
            "ResultsByTime": [{
                "TimePeriod": {"Start": "2026-08-01", "End": "2026-08-02"},
                "Groups": [{
                    "Keys": ["Amazon Elastic Compute Cloud - Compute", "us-east-1"],
                    "Metrics": {"UnblendedCost": {"Amount": "12.34", "Unit": "USD"}},
                }],
            }]
        }
        result = fetch_aws_costs(
            provider,
            account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
        )
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].amount, Decimal("12.34"))
        self.assertEqual(result.records[0].region, "us-east-1")


class CostApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="password")
        Group.objects.get_or_create(name=PLATFORM_ADMIN)[0].user_set.add(self.admin)
        org = Organization.objects.create(name="Cost Org")
        node = OrganizationNode.objects.create(organization=org, name="Cloud")
        project = Project.objects.create(organization=org, node=node, name="FinOps")
        self.account = CloudAccount.objects.create(
            organization=org,
            project=project,
            name="Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.client.force_authenticate(self.admin)

    @patch("core.costs.get_provider")
    def test_cost_sync_is_idempotent(self, provider_factory):
        provider = MagicMock()
        provider.fetch_costs.return_value = CostResult(records=[
            ProviderCostRecord(
                usage_date=date(2026, 8, 1),
                provider_account_id="123456789012",
                service="Amazon EC2",
                region="us-east-1",
                amount=Decimal("5.25"),
                currency="USD",
            )
        ])
        provider_factory.return_value = provider
        payload = {"start_date": "2026-08-01", "end_date": "2026-08-02"}
        url = f"/api/cloud-accounts/{self.account.id}/sync-costs/"
        self.assertEqual(self.client.post(url, payload, format="json").status_code, 200)
        self.assertEqual(self.client.post(url, payload, format="json").status_code, 200)
        self.assertEqual(CostRecord.objects.count(), 1)
        self.assertEqual(CostRecord.objects.get().amount, Decimal("5.25"))

    def test_summary_and_csv_use_normalized_records(self):
        CostRecord.objects.create(
            provider="aws",
            cloud_account=self.account,
            project=self.account.project,
            provider_account_id=self.account.provider_account_id,
            usage_date=timezone.localdate(),
            service="Amazon EC2",
            region="us-east-1",
            amount=Decimal("7.50"),
            currency="USD",
            updated_at=timezone.now(),
        )
        summary = self.client.get("/api/costs/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(Decimal(str(summary.data["total"])), Decimal("7.50"))
        export = self.client.get("/api/costs/export/")
        self.assertEqual(export.status_code, 200)
        self.assertIn("Amazon EC2", export.content.decode())

    def test_cost_sync_requires_validated_account(self):
        self.account.status = CloudAccount.Status.UNVALIDATED
        self.account.save(update_fields=["status"])
        response = self.client.post(
            f"/api/cloud-accounts/{self.account.id}/sync-costs/",
            {"start_date": "2026-08-01", "end_date": "2026-08-02"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
