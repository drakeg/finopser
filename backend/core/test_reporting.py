from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import CloudAccount, CloudResource, CostRecord, Organization, OrganizationNode, Project
from .report_models import ReportGeneration


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
        self.assertEqual(reports["resource-inventory"]["endpoint"], "/api/reports/resource-inventory.csv")
        self.assertEqual(reports["cost-detail"]["target"], "Costs")
        self.assertEqual(reports["cost-detail"]["endpoint"], "/api/reports/cost-detail.csv")
        self.assertNotIn("organization", reports["resource-inventory"])
        self.assertNotIn("credentials", reports["resource-inventory"])

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


    def test_report_schedule_lifecycle_is_tenant_scoped_and_audited(self):
        created = self.client.post(
            "/api/report-schedules/",
            {"name": "Weekly inventory", "report_code": "resource-inventory", "cadence": "weekly"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        schedule_id = created.json()["id"]
        self.assertTrue(created.json()["is_active"])
        self.assertEqual(self.organization.report_schedules.count(), 1)
        self.assertEqual(self.other.report_schedules.count(), 0)

        disabled = self.client.post(f"/api/report-schedules/{schedule_id}/disable/", {}, format="json")
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.json()["is_active"])
        enabled = self.client.post(f"/api/report-schedules/{schedule_id}/enable/", {}, format="json")
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.json()["is_active"])

        actions = set(
            self.organization.audit_events.filter(object_type="ReportSchedule").values_list("action", flat=True)
        )
        self.assertEqual(
            actions,
            {"report_schedule.create", "report_schedule.disable", "report_schedule.enable"},
        )

    def test_report_schedule_rejects_unsupported_report_and_member_mutation(self):
        unsupported = self.client.post(
            "/api/report-schedules/",
            {"name": "Unknown", "report_code": "not-a-report", "cadence": "daily"},
            format="json",
        )
        self.assertEqual(unsupported.status_code, 400)

        member = User.objects.create_user(username="report-member", password="test-password-long")
        OrganizationMembership.objects.create(
            user=member,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        self.client.logout()
        self.client.login(username=member.username, password="test-password-long")
        denied = self.client.post(
            "/api/report-schedules/",
            {"name": "Daily inventory", "report_code": "resource-inventory", "cadence": "daily"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.client.get("/api/report-schedules/").status_code, 200)

    def test_generation_history_contains_metadata_only_and_is_tenant_scoped(self):
        schedule = self.organization.report_schedules.create(
            name="Monthly inventory",
            report_code="resource-inventory",
            cadence="monthly",
            created_by=self.user,
        )
        ReportGeneration.objects.create(
            organization=self.organization,
            schedule=schedule,
            report_code="resource-inventory",
            status=ReportGeneration.Status.SUCCEEDED,
            row_count=42,
            truncated=False,
            requested_by=self.user,
        )
        ReportGeneration.objects.create(
            organization=self.other,
            report_code="resource-inventory",
            status=ReportGeneration.Status.SUCCEEDED,
            row_count=999,
        )

        response = self.client.get("/api/report-generations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        payload = response.json()[0]
        self.assertEqual(payload["row_count"], 42)
        self.assertEqual(
            set(payload),
            {"id", "schedule", "report_code", "status", "row_count", "truncated", "generated_at"},
        )


    def test_manager_explicitly_generates_metadata_without_persisting_csv(self):
        schedule = self.organization.report_schedules.create(
            name="Manual inventory",
            report_code="resource-inventory",
            cadence="weekly",
            created_by=self.user,
        )
        response = self.client.post(f"/api/report-schedules/{schedule.id}/generate/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["report_code"], "resource-inventory")
        self.assertEqual(response.json()["row_count"], 1)
        generation = ReportGeneration.objects.get(pk=response.json()["id"])
        self.assertEqual(generation.organization, self.organization)
        self.assertEqual(generation.requested_by, self.user)
        self.assertFalse(hasattr(generation, "content"))
        self.assertFalse(hasattr(generation, "csv"))
        event = self.organization.audit_events.get(action="report_generation.create")
        self.assertEqual(event.metadata["report"], "resource-inventory")
        self.assertNotIn("content", event.metadata)

    def test_explicit_generation_fails_closed_for_disabled_cross_tenant_and_member(self):
        schedule = self.organization.report_schedules.create(
            name="Disabled inventory",
            report_code="resource-inventory",
            cadence="daily",
            is_active=False,
            created_by=self.user,
        )
        self.assertEqual(
            self.client.post(f"/api/report-schedules/{schedule.id}/generate/", {}, format="json").status_code,
            404,
        )

        other_schedule = self.other.report_schedules.create(
            name="Other tenant",
            report_code="resource-inventory",
            cadence="daily",
            created_by=self.other_user,
        )
        self.assertEqual(
            self.client.post(f"/api/report-schedules/{other_schedule.id}/generate/", {}, format="json").status_code,
            404,
        )

        member = User.objects.create_user(username="generation-member", password="test-password-long")
        OrganizationMembership.objects.create(
            user=member,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        schedule.is_active = True
        schedule.save(update_fields=["is_active"])
        self.client.logout()
        self.client.login(username=member.username, password="test-password-long")
        self.assertEqual(
            self.client.post(f"/api/report-schedules/{schedule.id}/generate/", {}, format="json").status_code,
            403,
        )
