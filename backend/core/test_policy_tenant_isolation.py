from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .account_models import OrganizationMembership, Subscription
from .models import (
    CloudAccount,
    CloudResource,
    GovernancePolicy,
    Organization,
    OrganizationNode,
    Project,
)
from .rbac import SECURITY_ENGINEER


class PolicyTenantIsolationTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="policy-a", password="password")
        self.user_b = User.objects.create_user(username="policy-b", password="password")
        group = Group.objects.get_or_create(name=SECURITY_ENGINEER)[0]
        group.user_set.add(self.user_a, self.user_b)

        self.org_a, self.account_a = self._workspace("Policy Tenant A", "111111111111")
        self.org_b, self.account_b = self._workspace("Policy Tenant B", "222222222222")
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
            plan=Subscription.Plan.BUSINESS,
            status=Subscription.Status.ACTIVE,
        )
        Subscription.objects.create(
            organization=self.org_b,
            plan=Subscription.Plan.BUSINESS,
            status=Subscription.Status.ACTIVE,
        )

        self.resource_a = self._resource(self.account_a, "tenant-a-public")
        self.resource_b = self._resource(self.account_b, "tenant-b-public")
        self.client.force_authenticate(self.user_a)

    def _workspace(self, name, account_id):
        organization = Organization.objects.create(name=name)
        node = OrganizationNode.objects.create(organization=organization, name="Platform")
        project = Project.objects.create(organization=organization, node=node, name="Core")
        account = CloudAccount.objects.create(
            organization=organization,
            project=project,
            name=f"AWS {name}",
            provider_account_id=account_id,
            role_arn=f"arn:aws:iam::{account_id}:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        return organization, account

    def _resource(self, account, name):
        return CloudResource.objects.create(
            provider="aws",
            cloud_account=account,
            provider_resource_id=f"test:{name}",
            resource_type="aws.ec2.instance",
            name=name,
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={"public_ip_address": "203.0.113.10"},
        )

    def test_evaluation_and_aggregates_do_not_cross_tenants(self):
        response = self.client.post("/api/policies/evaluate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["violated_count"], 1)

        violations = self.client.get("/api/policy-violations/")
        self.assertEqual(violations.status_code, 200)
        self.assertEqual(len(violations.data), 1)
        self.assertEqual(violations.data[0]["cloud_account"], self.account_a.id)

        summary = self.client.get("/api/policies/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["violations"]["open"], 1)

    def test_policy_reads_and_writes_are_workspace_scoped(self):
        GovernancePolicy.objects.create(
            code="TENANT-B-ONLY",
            name="Tenant B only",
            severity=GovernancePolicy.Severity.HIGH,
            mode=GovernancePolicy.Mode.OBSERVE,
            enabled=True,
            resource_type="aws.ec2.instance",
            rule_key="ec2_public_ipv4",
            organization=self.org_b,
            created_by=self.user_b,
        )

        response = self.client.get("/api/policies/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("TENANT-B-ONLY", {item["code"] for item in response.data})

        create = self.client.post(
            "/api/policies/",
            {
                "code": "CROSS-TENANT",
                "name": "Cross tenant",
                "severity": "high",
                "mode": "observe",
                "enabled": True,
                "resource_type": "aws.ec2.instance",
                "rule_key": "ec2_public_ipv4",
                "organization": self.org_b.id,
                "cloud_account": self.account_b.id,
            },
            format="json",
        )
        self.assertEqual(create.status_code, 403)
        self.assertFalse(GovernancePolicy.objects.filter(code="CROSS-TENANT").exists())

    def test_run_history_isolated_by_workspace(self):
        self.assertEqual(self.client.post("/api/policies/evaluate/").status_code, 200)

        self.client.force_authenticate(self.user_b)
        self.assertEqual(self.client.post("/api/policies/evaluate/").status_code, 200)
        runs_b = self.client.get("/api/policy-runs/")
        self.assertEqual(runs_b.status_code, 200)
        self.assertEqual(len(runs_b.data), 1)

        self.client.force_authenticate(self.user_a)
        runs_a = self.client.get("/api/policy-runs/")
        self.assertEqual(runs_a.status_code, 200)
        self.assertEqual(len(runs_a.data), 1)
        self.assertNotEqual(runs_a.data[0]["id"], runs_b.data[0]["id"])
