from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

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
