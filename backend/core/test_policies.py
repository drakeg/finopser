from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    CloudAccount,
    CloudResource,
    GovernancePolicy,
    Organization,
    OrganizationNode,
    PolicyViolation,
    Project,
)
from .policies import evaluate_policies
from .rbac import AUDITOR, SECURITY_ENGINEER


class PolicyGuardrailTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="security", password="password")
        Group.objects.get_or_create(name=SECURITY_ENGINEER)[0].user_set.add(self.user)
        self.client.force_authenticate(self.user)
        self.org = Organization.objects.create(name="Policy Org")
        self.node = OrganizationNode.objects.create(organization=self.org, name="Platform")
        self.project = Project.objects.create(organization=self.org, node=self.node, name="Core")
        self.account = CloudAccount.objects.create(
            organization=self.org,
            project=self.project,
            name="Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )

    def resource(self, name, resource_type, metadata):
        return CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id=f"test:{name}",
            resource_type=resource_type,
            name=name,
            region="us-east-1",
            state="available",
            is_active=True,
            last_seen=timezone.now(),
            metadata=metadata,
        )

    @patch("core.providers.aws.boto3.client")
    def test_evaluation_uses_persisted_evidence_only(self, client_mock):
        self.resource("web", "aws.ec2.instance", {"public_ip_address": "203.0.113.10"})
        response = self.client.post("/api/policies/evaluate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["violated_count"], 1)
        violation = PolicyViolation.objects.get(policy__code="GUARD-EC2-PUBLIC-IP")
        self.assertEqual(violation.evidence["public_ip_address"], "203.0.113.10")
        client_mock.assert_not_called()

    def test_missing_evidence_is_unknown_not_violation(self):
        self.resource("legacy", "aws.ec2.instance", {})
        run = evaluate_policies(self.user)
        self.assertEqual(run.unknown_count, 1)
        self.assertEqual(PolicyViolation.objects.count(), 0)

    def test_passing_evidence_resolves_prior_violation(self):
        resource = self.resource(
            "db",
            "aws.rds.db_instance",
            {"publicly_accessible": True, "storage_encrypted": True},
        )
        evaluate_policies(self.user)
        violation = PolicyViolation.objects.get(
            policy__code="GUARD-RDS-PUBLIC",
            resource=resource,
        )
        self.assertEqual(violation.status, PolicyViolation.Status.OPEN)
        resource.metadata["publicly_accessible"] = False
        resource.save(update_fields=["metadata"])
        run = evaluate_policies(self.user)
        violation.refresh_from_db()
        self.assertEqual(violation.status, PolicyViolation.Status.RESOLVED)
        self.assertGreaterEqual(run.resolved_count, 1)

    def test_account_scope_excludes_other_accounts(self):
        other = CloudAccount.objects.create(
            organization=self.org,
            project=self.project,
            name="Other",
            provider_account_id="210987654321",
            role_arn="arn:aws:iam::210987654321:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.resource("scoped", "aws.ec2.instance", {"public_ip_address": "203.0.113.20"})
        CloudResource.objects.create(
            provider="aws",
            cloud_account=other,
            provider_resource_id="test:other",
            resource_type="aws.ec2.instance",
            name="other",
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={"public_ip_address": "203.0.113.21"},
        )
        policy = GovernancePolicy.objects.get(code="GUARD-EC2-PUBLIC-IP")
        policy.cloud_account = self.account
        policy.save(update_fields=["cloud_account"])
        run = evaluate_policies(self.user)
        self.assertEqual(run.violated_count, 1)
        self.assertEqual(
            PolicyViolation.objects.filter(policy=policy, status="open").count(),
            1,
        )

    def test_auditor_cannot_write_or_evaluate(self):
        auditor = User.objects.create_user(username="auditor", password="password")
        Group.objects.get_or_create(name=AUDITOR)[0].user_set.add(auditor)
        self.client.force_authenticate(auditor)
        self.assertEqual(self.client.post("/api/policies/evaluate/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/policies/", {"code": "CUSTOM"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/policies/summary/").status_code, 200)
