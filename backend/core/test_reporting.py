from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import CloudAccount, CloudResource, CostRecord, Organization, OrganizationNode, Project


class ReportingFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="report-user", password="test-password-long")
        self.organization = Organization.objects.create(name="Reporting Workspace")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        self.project = Project.objects.create(organization=self.organization, node=node, name="Default")
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            project=self.project,
            name="Primary AWS",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id="ec2:123456789012:us-east-1:i-0123456789abcdef0",
            resource_type="aws.ec2.instance",
            name="web-1",
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={},
            tags={"Owner": "platform"},
        )
        self.cost = CostRecord.objects.create(
            provider="aws",
            cloud_account=self.account,
            project=self.project,
            provider_account_id=self.account.provider_account_id,
            usage_date=date(2026, 8, 15),
            service="AmazonEC2",
            region="us-east-1",
            amount=Decimal("12.34000000"),
            currency="USD",
            updated_at=timezone.now(),
        )
        self.other = Organization.objects.create(name="Other Reporting Workspace")
        other_node = OrganizationNode.objects.create(organization=self.other, name="Root")
        other_project = Project.objects.create(
            organization=self.other,
            node=other_node,
            name="Default",
        )
        other_account = CloudAccount.objects.create(
            organization=self.other,
            project=other_project,
            name="Other AWS",
            provider_account_id="210987654321",
            role_arn="arn:aws:iam::210987654321:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        CloudResource.objects.create(
            provider="aws",
            cloud_account=other_account,
            provider_resource_id="ec2:210987654321:us-west-2:i-0fedcba9876543210",
            resource_type="aws.ec2.instance",
            name="secret-other-tenant",
            region="us-west-2",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={},
            tags={},
        )
        CostRecord.objects.create(
            provider="aws",
            cloud_account=other_account,
            project=other_project,
            provider_account_id=other_account.provider_account_id,
            usage_date=date(2026, 8, 15),
            service="SecretOtherTenantService",
            region="us-west-2",
            amount=Decimal("999.99000000"),
            currency="USD",
            updated_at=timezone.now(),
        )
        self.client = APIClient()
        self.client.login(username=self.user.username, password="test-password-long")

    def test_catalog_exposes_supported_reports(self):
        response = self.client.get("/api/reports/")
        self.assertEqual(response.status_code, 200)
        reports = {report["code"]: report for report in response.json()["reports"]}
        self.assertEqual(reports["resource-inventory"]["format"], "csv")
        self.assertEqual(reports["cost-detail"]["target"], "Costs")

    def test_resource_inventory_csv_is_tenant_scoped_and_deterministic(self):
        response = self.client.get("/api/reports/resource-inventory.csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(response["X-Finopser-Row-Count"], "1")
        content = response.content.decode()
        self.assertTrue(
            content.startswith(
                "account,provider,provider_resource_id,resource_type,name,region,state,is_active,last_seen\n"
            )
        )
        self.assertIn("Primary AWS,aws", content)
        self.assertIn("web-1", content)
        self.assertNotIn("secret-other-tenant", content)

    def test_resource_inventory_filters_apply_within_tenant(self):
        inactive = CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id="arn:aws:s3:::archive-bucket",
            resource_type="aws.s3.bucket",
            name="archive-bucket",
            region="global",
            state="available",
            is_active=False,
            last_seen=timezone.now(),
            metadata={},
            tags={},
        )

        response = self.client.get(
            "/api/reports/resource-inventory.csv",
            {"resource_type": "aws.s3.bucket", "active": "false"},
        )

        content = response.content.decode()
        self.assertEqual(response["X-Finopser-Row-Count"], "1")
        self.assertIn(inactive.provider_resource_id, content)
        self.assertNotIn(self.resource.provider_resource_id, content)

    def test_cost_detail_csv_is_tenant_scoped_and_deterministic(self):
        response = self.client.get("/api/reports/cost-detail.csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Finopser-Report"], "cost-detail")
        self.assertEqual(response["X-Finopser-Row-Count"], "1")
        content = response.content.decode()
        self.assertTrue(
            content.startswith(
                "usage_date,account,provider_account_id,project,service,region,amount,currency,updated_at\n"
            )
        )
        self.assertIn("2026-08-15,Primary AWS,123456789012,Default,AmazonEC2,us-east-1,12.34000000,USD", content)
        self.assertNotIn("SecretOtherTenantService", content)

    def test_cost_detail_filters_and_date_validation(self):
        CostRecord.objects.create(
            provider="aws",
            cloud_account=self.account,
            project=self.project,
            provider_account_id=self.account.provider_account_id,
            usage_date=date(2026, 8, 20),
            service="AmazonS3",
            region="global",
            amount=Decimal("3.50000000"),
            currency="USD",
            updated_at=timezone.now(),
        )
        response = self.client.get(
            "/api/reports/cost-detail.csv",
            {"service": "AmazonS3", "start_date": "2026-08-18", "end_date": "2026-08-31"},
        )
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Finopser-Row-Count"], "1")
        self.assertIn("AmazonS3", content)
        self.assertNotIn("AmazonEC2", content)

        invalid = self.client.get(
            "/api/reports/cost-detail.csv",
            {"start_date": "2026-09-01", "end_date": "2026-08-01"},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("end_date", invalid.json())

    def test_report_export_records_audit_event(self):
        response = self.client.get("/api/reports/resource-inventory.csv")
        self.assertEqual(response.status_code, 200)
        event = self.organization.audit_events.get(action="report.export")
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.metadata["report"], "resource-inventory")
        self.assertEqual(event.metadata["row_count"], 1)
