from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    CloudAccount,
    CloudResource,
    CostRecord,
    CostSync,
    InventorySync,
    Organization,
    OrganizationNode,
    Project,
)
from .rbac import AUDITOR


class OperationalDashboardTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="auditor", password="password")
        Group.objects.get_or_create(name=AUDITOR)[0].user_set.add(self.user)
        self.client.force_authenticate(self.user)
        self.org = Organization.objects.create(name="Dashboard Org")
        self.node = OrganizationNode.objects.create(organization=self.org, name="Cloud")
        self.project = Project.objects.create(
            organization=self.org,
            node=self.node,
            name="Platform",
        )

    def _account(self, *, name="Production", status=CloudAccount.Status.VALID):
        return CloudAccount.objects.create(
            organization=self.org,
            project=self.project,
            name=name,
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=status,
        )

    def test_anonymous_dashboard_is_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/dashboard/")
        self.assertIn(response.status_code, (401, 403))

    @patch("core.providers.aws.boto3.client")
    def test_dashboard_uses_persisted_data_without_aws_calls(self, client_mock):
        account = self._account()
        today = timezone.localdate()
        now = timezone.now()
        CostRecord.objects.create(
            provider="aws",
            cloud_account=account,
            project=self.project,
            provider_account_id=account.provider_account_id,
            usage_date=today,
            service="Amazon EC2",
            region="us-east-1",
            amount=Decimal("12.34000000"),
            currency="USD",
            updated_at=now,
        )
        CloudResource.objects.create(
            provider="aws",
            cloud_account=account,
            provider_resource_id="ec2:123456789012:us-east-1:i-test",
            resource_type="aws.ec2.instance",
            name="web-1",
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=now,
        )

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["spend"]["mtd"]), Decimal("12.34000000"))
        self.assertEqual(response.data["resources"]["active"], 1)
        self.assertEqual(response.data["top_costs"]["service"][0]["service"], "Amazon EC2")
        client_mock.assert_not_called()

    def test_empty_dashboard_is_useful(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["spend"]["mtd"]), Decimal("0"))
        self.assertEqual(response.data["resources"]["total"], 0)
        self.assertEqual(response.data["accounts"]["total"], 0)
        self.assertEqual(response.data["attention"], [])

    def test_attention_is_evidence_backed_and_severity_ordered(self):
        account = self._account(status=CloudAccount.Status.INVALID)
        account.last_error = "AWS validation failed: AccessDenied"
        account.save(update_fields=["last_error"])
        now = timezone.now()
        InventorySync.objects.create(
            cloud_account=account,
            status=InventorySync.Status.PARTIAL,
            started_at=now,
            completed_at=now,
            errors=["ec2:us-east-1:AccessDenied"],
        )
        CostSync.objects.create(
            cloud_account=account,
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            status=CostSync.Status.FAILED,
            started_at=now,
            completed_at=now,
            errors=["ce:AccessDenied"],
        )
        CloudResource.objects.create(
            provider="aws",
            cloud_account=account,
            provider_resource_id="arn:aws:s3:::old-bucket",
            resource_type="aws.s3.bucket",
            name="old-bucket",
            region="global",
            state="available",
            is_active=False,
            last_seen=now,
        )

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        severities = [item["severity"] for item in response.data["attention"]]
        self.assertEqual(severities[:2], ["high", "high"])
        self.assertIn("medium", severities)
        self.assertEqual(severities[-1], "low")
        kinds = {item["kind"] for item in response.data["attention"]}
        self.assertTrue({"account_validation", "inventory_sync", "cost_sync", "inactive_resources"}.issubset(kinds))
