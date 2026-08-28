from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .account_models import OrganizationMembership, Subscription
from .models import (
    CloudAccount,
    CloudResource,
    ComplianceControl,
    ComplianceException,
    ComplianceFinding,
    Organization,
    OrganizationNode,
    Project,
)
from .rbac import PLATFORM_ADMIN


class ComplianceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="compliance-admin", password="password")
        Group.objects.get_or_create(name=PLATFORM_ADMIN)[0].user_set.add(self.user)
        self.client.force_authenticate(self.user)
        self.org = Organization.objects.create(name="Compliance Org")
        self.node = OrganizationNode.objects.create(organization=self.org, name="Cloud")
        self.project = Project.objects.create(
            organization=self.org,
            node=self.node,
            name="Production",
        )
        self.account = CloudAccount.objects.create(
            organization=self.org,
            project=self.project,
            name="AWS Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )

    def _resource(self, resource_id, resource_type, metadata):
        return CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id=resource_id,
            resource_type=resource_type,
            name=resource_id.rsplit(":", 1)[-1],
            region="us-east-1",
            state="available",
            is_active=True,
            last_seen=timezone.now(),
            metadata=metadata,
        )

    @patch("core.providers.aws.boto3.client")
    def test_evaluation_uses_only_persisted_evidence(self, client_mock):
        self._resource(
            "ec2:123456789012:us-east-1:i-public",
            "aws.ec2.instance",
            {"public_ip_address": "203.0.113.10"},
        )
        self._resource(
            "arn:aws:rds:us-east-1:123456789012:db:unsafe",
            "aws.rds.db_instance",
            {"publicly_accessible": True, "storage_encrypted": False},
        )

        response = self.client.post("/api/compliance/evaluate/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["failed_count"], 3)
        self.assertEqual(response.data["unknown_count"], 0)
        self.assertEqual(ComplianceFinding.objects.filter(status="open").count(), 3)
        client_mock.assert_not_called()

    def test_missing_evidence_is_unknown_not_failure(self):
        self._resource(
            "ec2:123456789012:us-east-1:i-legacy",
            "aws.ec2.instance",
            {},
        )

        response = self.client.post("/api/compliance/evaluate/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["unknown_count"], 1)
        self.assertEqual(response.data["failed_count"], 0)
        self.assertEqual(ComplianceFinding.objects.count(), 0)

    def test_passing_evidence_resolves_existing_finding(self):
        resource = self._resource(
            "ec2:123456789012:us-east-1:i-changing",
            "aws.ec2.instance",
            {"public_ip_address": "203.0.113.20"},
        )
        self.client.post("/api/compliance/evaluate/")
        finding = ComplianceFinding.objects.get(resource=resource)
        self.assertEqual(finding.status, ComplianceFinding.Status.OPEN)

        resource.metadata = {"public_ip_address": ""}
        resource.save(update_fields=["metadata"])
        response = self.client.post("/api/compliance/evaluate/")

        finding.refresh_from_db()
        self.assertEqual(response.data["resolved_count"], 1)
        self.assertEqual(finding.status, ComplianceFinding.Status.RESOLVED)
        self.assertIsNotNone(finding.resolved_at)

    def test_active_exception_marks_failure_excepted(self):
        resource = self._resource(
            "ec2:123456789012:us-east-1:i-excepted",
            "aws.ec2.instance",
            {"public_ip_address": "203.0.113.30"},
        )
        self.client.post("/api/compliance/evaluate/")
        control = ComplianceControl.objects.get(code="AWS-EC2-001")
        ComplianceException.objects.create(
            control=control,
            resource=resource,
            reason="Temporary vendor access window",
            created_by=self.user,
        )

        self.client.post("/api/compliance/evaluate/")

        finding = ComplianceFinding.objects.get(control=control, resource=resource)
        self.assertEqual(finding.status, ComplianceFinding.Status.EXCEPTED)

    def test_summary_and_reads_require_authentication(self):
        response = self.client.get("/api/compliance/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["controls"], 3)

        self.client.force_authenticate(user=None)
        response = self.client.get("/api/compliance/summary/")
        self.assertIn(response.status_code, (401, 403))


class ComplianceTenantIsolationTests(APITestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=PLATFORM_ADMIN)
        self.user_a = User.objects.create_user(username="tenant-a", password="password123")
        self.user_b = User.objects.create_user(username="tenant-b", password="password123")
        self.admin_group.user_set.add(self.user_a, self.user_b)
        self.org_a, self.account_a = self._workspace("Tenant A", "111111111111")
        self.org_b, self.account_b = self._workspace("Tenant B", "222222222222")
        OrganizationMembership.objects.create(
            user=self.user_a,
            organization=self.org_a,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            user=self.user_b,
            organization=self.org_b,
            role=OrganizationMembership.Role.OWNER,
        )
        Subscription.objects.create(
            organization=self.org_a,
            plan=Subscription.Plan.PRO,
            status=Subscription.Status.ACTIVE,
        )
        Subscription.objects.create(
            organization=self.org_b,
            plan=Subscription.Plan.PRO,
            status=Subscription.Status.ACTIVE,
        )
        self.resource_a = self._resource(self.account_a, "i-tenant-a")
        self.resource_b = self._resource(self.account_b, "i-tenant-b")

    def _workspace(self, name, account_id):
        organization = Organization.objects.create(name=name)
        node = OrganizationNode.objects.create(organization=organization, name="Root")
        project = Project.objects.create(organization=organization, node=node, name="Default")
        account = CloudAccount.objects.create(
            organization=organization,
            project=project,
            name=name,
            provider_account_id=account_id,
            role_arn=f"arn:aws:iam::{account_id}:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        return organization, account

    def _resource(self, account, name):
        return CloudResource.objects.create(
            provider="aws",
            cloud_account=account,
            provider_resource_id=f"ec2:{account.provider_account_id}:us-east-1:{name}",
            resource_type="aws.ec2.instance",
            name=name,
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={"public_ip_address": "203.0.113.10"},
        )

    def test_evaluation_findings_summary_and_runs_are_isolated(self):
        self.client.login(username="tenant-b", password="password123")
        response_b = self.client.post("/api/compliance/evaluate/")
        self.assertEqual(response_b.status_code, 200)
        self.client.logout()

        self.client.login(username="tenant-a", password="password123")
        response_a = self.client.post("/api/compliance/evaluate/")
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_a.data["failed_count"], 1)

        findings = self.client.get("/api/compliance/findings/")
        self.assertEqual(findings.status_code, 200)
        self.assertEqual(len(findings.data), 1)
        self.assertEqual(findings.data[0]["cloud_account"], self.account_a.id)

        summary = self.client.get("/api/compliance/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["findings"]["open"], 1)

        runs = self.client.get("/api/compliance/runs/")
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(len(runs.data), 1)
        self.assertEqual(runs.data[0]["id"], response_a.data["id"])

    def test_exception_cannot_reference_other_workspace(self):
        self.client.login(username="tenant-a", password="password123")
        self.client.post("/api/compliance/evaluate/")
        control = ComplianceControl.objects.get(code="AWS-EC2-001")
        response = self.client.post(
            "/api/compliance/exceptions/",
            {
                "control": control.id,
                "resource": self.resource_b.id,
                "reason": "Cross tenant attempt",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ComplianceException.objects.filter(resource=self.resource_b).exists())
