from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .account_models import OrganizationMembership, Subscription
from .automation_models import RemediationAction
from .models import CloudAccount, CloudResource, Organization, OrganizationNode, Project
from .recommendation_models import Recommendation


class ActionReportingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="action-report-user", password="test-password-long")
        self.organization = Organization.objects.create(name="Action Reporting Workspace")
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        project = Project.objects.create(organization=self.organization, node=node, name="Default")
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            project=project,
            name="Primary AWS",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id="ec2:123456789012:us-east-1:i-report",
            resource_type="aws.ec2.instance",
            name="report-instance",
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={},
            tags={},
        )
        now = timezone.now()
        self.recommendation = Recommendation.objects.create(
            organization=self.organization,
            source_key="report-rec",
            source_type="test",
            category=Recommendation.Category.COST,
            priority=Recommendation.Priority.HIGH,
            status=Recommendation.Status.OPEN,
            title="Rightsize instance",
            detail="Persisted evidence supports review.",
            action="Review instance size",
            estimated_monthly_savings="12.34",
            cloud_account=self.account,
            project=project,
            resource=self.resource,
            first_seen=now,
            last_seen=now,
            evidence={},
        )
        self.remediation = RemediationAction.objects.create(
            recommendation=self.recommendation,
            resource=self.resource,
            cloud_account=self.account,
            action_key="add_tags",
            status=RemediationAction.Status.SUCCEEDED,
            simulation=True,
            requested_by=self.user,
            parameters={"secret": "not-exported"},
            preview={},
            provider_result={"secret": "not-exported"},
        )

        other = Organization.objects.create(name="Other Action Reporting Workspace")
        other_node = OrganizationNode.objects.create(organization=other, name="Root")
        other_project = Project.objects.create(organization=other, node=other_node, name="Default")
        other_account = CloudAccount.objects.create(
            organization=other,
            project=other_project,
            name="Other AWS",
            provider_account_id="210987654321",
            role_arn="arn:aws:iam::210987654321:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        other_resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=other_account,
            provider_resource_id="ec2:210987654321:us-west-2:i-secret",
            resource_type="aws.ec2.instance",
            name="secret-other-tenant",
            region="us-west-2",
            state="running",
            is_active=True,
            last_seen=now,
            metadata={},
            tags={},
        )
        other_rec = Recommendation.objects.create(
            organization=other,
            source_key="other-report-rec",
            source_type="test",
            category=Recommendation.Category.OPERATIONS,
            priority=Recommendation.Priority.CRITICAL,
            status=Recommendation.Status.OPEN,
            title="secret-other-recommendation",
            detail="other tenant",
            action="other action",
            cloud_account=other_account,
            project=other_project,
            resource=other_resource,
            first_seen=now,
            last_seen=now,
            evidence={},
        )
        RemediationAction.objects.create(
            recommendation=other_rec,
            resource=other_resource,
            cloud_account=other_account,
            action_key="secret-other-remediation",
            status=RemediationAction.Status.FAILED,
            simulation=True,
            parameters={},
            preview={},
            provider_result={},
        )
        self.client = APIClient()
        self.client.login(username=self.user.username, password="test-password-long")

    def _enable_pro(self):
        subscription, _ = Subscription.objects.get_or_create(organization=self.organization)
        subscription.plan = Subscription.Plan.PRO
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["plan", "status", "updated_at"])

    def test_free_plan_hides_and_denies_action_reports(self):
        codes = {item["code"] for item in self.client.get("/api/reports/").json()["reports"]}
        self.assertNotIn("recommendations", codes)
        self.assertNotIn("remediation-history", codes)
        self.assertEqual(self.client.get("/api/reports/recommendations.csv").status_code, 403)
        self.assertEqual(self.client.get("/api/reports/remediation-history.csv").status_code, 403)

    def test_pro_plan_action_reports_are_tenant_scoped_and_omit_payloads(self):
        self._enable_pro()
        codes = {item["code"] for item in self.client.get("/api/reports/").json()["reports"]}
        self.assertIn("recommendations", codes)
        self.assertIn("remediation-history", codes)

        recommendations = self.client.get("/api/reports/recommendations.csv", {"status": "open"})
        self.assertEqual(recommendations.status_code, 200)
        rec_content = recommendations.content.decode()
        self.assertIn("Rightsize instance", rec_content)
        self.assertNotIn("secret-other-recommendation", rec_content)
        self.assertNotIn("Persisted evidence supports review", rec_content)

        remediations = self.client.get("/api/reports/remediation-history.csv", {"simulation": "true"})
        self.assertEqual(remediations.status_code, 200)
        remediation_content = remediations.content.decode()
        self.assertIn("add_tags", remediation_content)
        self.assertNotIn("secret-other-remediation", remediation_content)
        self.assertNotIn("not-exported", remediation_content)
        self.assertEqual(remediations["X-Finopser-Report"], "remediation-history")
