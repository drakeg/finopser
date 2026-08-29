from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from .account_models import OrganizationMembership, Subscription
from .automation_models import RemediationAction
from .models import CloudAccount, CloudResource, Organization, OrganizationNode, Project
from .recommendation_models import Recommendation
from .remediation import ACTION_ADD_TAGS


class RemediationTenantIsolationTests(APITestCase):
    def _workspace(self, suffix):
        user = User.objects.create_user(username=f"remediation-{suffix}", password="password")
        organization = Organization.objects.create(name=f"Remediation Tenant {suffix}")
        node = OrganizationNode.objects.create(organization=organization, name="Root")
        project = Project.objects.create(organization=organization, node=node, name="Default")
        account = CloudAccount.objects.create(
            organization=organization,
            project=project,
            name=f"Account {suffix}",
            provider_account_id=f"{int(suffix):012d}",
            role_arn=f"arn:aws:iam::{int(suffix):012d}:role/FinopserAutomation",
            status=CloudAccount.Status.VALID,
        )
        resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=account,
            provider_resource_id=f"ec2:{suffix}:us-east-1:i-{suffix}",
            resource_type="aws.ec2.instance",
            name=f"instance-{suffix}",
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            tags={},
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        Subscription.objects.create(
            organization=organization,
            plan=Subscription.Plan.BUSINESS,
            status=Subscription.Status.ACTIVE,
        )
        return user, organization, project, account, resource

    def setUp(self):
        (
            self.user_a,
            self.org_a,
            self.project_a,
            self.account_a,
            self.resource_a,
        ) = self._workspace("301")
        (
            self.user_b,
            self.org_b,
            self.project_b,
            self.account_b,
            self.resource_b,
        ) = self._workspace("302")
        self.recommendation_b = Recommendation.objects.create(
            organization=self.org_b,
            source_key="tenant-b-remediation",
            source_type="untagged_resource",
            category=Recommendation.Category.GOVERNANCE,
            priority=Recommendation.Priority.LOW,
            status=Recommendation.Status.OPEN,
            title="Tenant B recommendation",
            detail="Tenant B only",
            action="Add tags",
            cloud_account=self.account_b,
            project=self.project_b,
            resource=self.resource_b,
            first_seen=timezone.now(),
            last_seen=timezone.now(),
        )
        self.action_a = RemediationAction.objects.create(
            resource=self.resource_a,
            cloud_account=self.account_a,
            action_key=ACTION_ADD_TAGS,
            simulation=True,
            parameters={"tags": {"Owner": "tenant-a"}},
            requested_by=self.user_a,
        )
        self.action_b = RemediationAction.objects.create(
            recommendation=self.recommendation_b,
            resource=self.resource_b,
            cloud_account=self.account_b,
            action_key=ACTION_ADD_TAGS,
            simulation=True,
            parameters={"tags": {"Owner": "tenant-b"}},
            requested_by=self.user_b,
        )
        self.client.force_authenticate(self.user_a)

    def test_list_retrieve_summary_and_actions_do_not_leak_other_workspace(self):
        response = self.client.get("/api/remediations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["id"] for item in response.data}, {self.action_a.id})
        self.assertEqual(self.client.get(f"/api/remediations/{self.action_b.id}/").status_code, 404)
        self.assertEqual(
            self.client.post(f"/api/remediations/{self.action_b.id}/preview/").status_code,
            404,
        )
        summary = self.client.get("/api/remediations/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["total"], 1)
        self.assertEqual(summary.data["simulation"], 1)

    def test_create_rejects_cross_workspace_targets(self):
        response = self.client.post(
            "/api/remediations/",
            {
                "recommendation": self.recommendation_b.id,
                "resource": self.resource_b.id,
                "cloud_account": self.account_b.id,
                "action_key": ACTION_ADD_TAGS,
                "simulation": True,
                "parameters": {"tags": {"Owner": "cross-tenant"}},
            },
            format="json",
        )
        self.assertIn(response.status_code, {400, 403})
        self.assertFalse(
            RemediationAction.objects.filter(
                requested_by=self.user_a,
                cloud_account=self.account_b,
            ).exists()
        )

    def test_create_rejects_mixed_tenant_recommendation_and_resource(self):
        response = self.client.post(
            "/api/remediations/",
            {
                "recommendation": self.recommendation_b.id,
                "resource": self.resource_a.id,
                "cloud_account": self.account_a.id,
                "action_key": ACTION_ADD_TAGS,
                "simulation": True,
                "parameters": {"tags": {"Owner": "tenant-a"}},
            },
            format="json",
        )
        self.assertIn(response.status_code, {400, 403})
