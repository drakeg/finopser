from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .account_models import OrganizationMembership, Subscription
from .models import CloudAccount, CloudResource, CostRecord, Organization, OrganizationNode, Project
from .rbac import AUDITOR, FINOPS_ANALYST
from .recommendation_models import Recommendation, RecommendationRun
from .recommendations import generate_recommendations


class RecommendationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="recommender", password="password")
        Group.objects.get_or_create(name=FINOPS_ANALYST)[0].user_set.add(self.user)
        self.client.force_authenticate(self.user)
        self.org = Organization.objects.create(name="Recommendation Org")
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

    def resource(self, name, tags=None):
        return CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id=f"test:{name}",
            resource_type="aws.ec2.instance",
            name=name,
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            tags={} if tags is None else tags,
        )

    def cost(self, amount, usage_date):
        return CostRecord.objects.create(
            provider="aws",
            cloud_account=self.account,
            project=self.project,
            provider_account_id=self.account.provider_account_id,
            usage_date=usage_date,
            service="AmazonEC2",
            region="us-east-1",
            amount=Decimal(amount),
            currency="USD",
            updated_at=timezone.now(),
        )

    @patch("core.providers.aws.boto3.client")
    def test_generation_uses_persisted_evidence_only(self, client_mock):
        self.resource("untagged")
        run = generate_recommendations(self.user, date(2026, 8, 20))
        self.assertEqual(run.open_count, 1)
        recommendation = Recommendation.objects.get(source_type="untagged_resource")
        self.assertEqual(recommendation.priority, Recommendation.Priority.LOW)
        client_mock.assert_not_called()

    def test_dismissed_recommendation_is_not_silently_reopened(self):
        self.resource("dismiss-me")
        generate_recommendations(self.user, date(2026, 8, 20))
        recommendation = Recommendation.objects.get()
        response = self.client.post(f"/api/recommendations/{recommendation.id}/dismiss/")
        self.assertEqual(response.status_code, 200)
        generate_recommendations(self.user, date(2026, 8, 20))
        recommendation.refresh_from_db()
        self.assertEqual(recommendation.status, Recommendation.Status.DISMISSED)

    def test_disappearing_open_condition_resolves(self):
        resource = self.resource("tag-later")
        generate_recommendations(self.user, date(2026, 8, 20))
        recommendation = Recommendation.objects.get()
        resource.tags = {"Owner": "platform"}
        resource.save(update_fields=["tags"])
        generate_recommendations(self.user, date(2026, 8, 20))
        recommendation.refresh_from_db()
        self.assertEqual(recommendation.status, Recommendation.Status.RESOLVED)

    def test_material_cost_growth_has_derived_monthly_savings(self):
        self.cost("100.00", date(2026, 7, 10))
        self.cost("160.00", date(2026, 8, 10))
        generate_recommendations(self.user, date(2026, 8, 20))
        recommendation = Recommendation.objects.get(source_type="cost_growth")
        self.assertEqual(recommendation.priority, Recommendation.Priority.HIGH)
        self.assertEqual(recommendation.estimated_monthly_savings, Decimal("93.00"))

    def test_auditor_can_read_but_cannot_generate_or_dismiss(self):
        self.resource("auditor-visible")
        generate_recommendations(self.user, date(2026, 8, 20))
        recommendation = Recommendation.objects.get()
        auditor = User.objects.create_user(username="recommendation-auditor", password="password")
        Group.objects.get_or_create(name=AUDITOR)[0].user_set.add(auditor)
        self.client.force_authenticate(auditor)
        self.assertEqual(self.client.get("/api/recommendations/").status_code, 200)
        self.assertEqual(self.client.get("/api/recommendations/summary/").status_code, 200)
        self.assertEqual(self.client.post("/api/recommendations/generate/").status_code, 403)
        self.assertEqual(
            self.client.post(f"/api/recommendations/{recommendation.id}/dismiss/").status_code,
            403,
        )


class RecommendationTenantIsolationTests(APITestCase):
    def _workspace(self, suffix):
        user = User.objects.create_user(username=f"recommendation-owner-{suffix}", password="password")
        organization = Organization.objects.create(name=f"Recommendation Tenant {suffix}")
        node = OrganizationNode.objects.create(organization=organization, name="Root")
        project = Project.objects.create(organization=organization, node=node, name="Default")
        account = CloudAccount.objects.create(
            organization=organization,
            project=project,
            name=f"Account {suffix}",
            provider_account_id=f"{int(suffix):012d}",
            role_arn=f"arn:aws:iam::{int(suffix):012d}:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        Subscription.objects.create(
            organization=organization,
            plan=Subscription.Plan.PRO,
            status=Subscription.Status.ACTIVE,
        )
        return user, organization, project, account

    def _resource(self, account, name, tags=None):
        return CloudResource.objects.create(
            provider="aws",
            cloud_account=account,
            provider_resource_id=f"test:{account.id}:{name}",
            resource_type="aws.ec2.instance",
            name=name,
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            tags={} if tags is None else tags,
        )

    def setUp(self):
        self.user_a, self.org_a, self.project_a, self.account_a = self._workspace("301")
        self.user_b, self.org_b, self.project_b, self.account_b = self._workspace("302")
        self.resource_a = self._resource(self.account_a, "resource-a")
        self.resource_b = self._resource(self.account_b, "resource-b")
        self.client.force_authenticate(self.user_a)

    def test_generation_and_summary_are_workspace_scoped(self):
        run = generate_recommendations(self.user_a, date(2026, 8, 20))
        self.assertEqual(run.organization, self.org_a)
        self.assertEqual(run.open_count, 1)
        self.assertTrue(Recommendation.objects.filter(organization=self.org_a).exists())
        self.assertFalse(Recommendation.objects.filter(organization=self.org_b).exists())

        summary = self.client.get("/api/recommendations/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["open"], 1)

    def test_list_retrieve_actions_and_run_history_hide_other_workspace(self):
        generate_recommendations(self.user_a, date(2026, 8, 20))
        generate_recommendations(self.user_b, date(2026, 8, 20))
        recommendation_a = Recommendation.objects.get(organization=self.org_a)
        recommendation_b = Recommendation.objects.get(organization=self.org_b)

        response = self.client.get("/api/recommendations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["id"] for item in response.data}, {recommendation_a.id})
        self.assertEqual(
            self.client.get(f"/api/recommendations/{recommendation_b.id}/").status_code,
            404,
        )
        self.assertEqual(
            self.client.post(f"/api/recommendations/{recommendation_b.id}/dismiss/").status_code,
            404,
        )

        runs = self.client.get("/api/recommendation-runs/")
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(len(runs.data), 1)
        self.assertEqual(RecommendationRun.objects.filter(organization=self.org_b).count(), 1)

    def test_generation_does_not_resolve_other_workspace_open_items(self):
        generate_recommendations(self.user_b, date(2026, 8, 20))
        recommendation_b = Recommendation.objects.get(organization=self.org_b)
        self.resource_b.tags = {"Owner": "tenant-b"}
        self.resource_b.save(update_fields=["tags"])

        generate_recommendations(self.user_a, date(2026, 8, 20))

        recommendation_b.refresh_from_db()
        self.assertEqual(recommendation_b.status, Recommendation.Status.OPEN)

    def test_source_keys_are_unique_per_workspace_not_globally(self):
        now = timezone.now()
        common = {
            "source_key": "shared-source-key",
            "source_type": "test",
            "category": Recommendation.Category.OPERATIONS,
            "priority": Recommendation.Priority.LOW,
            "status": Recommendation.Status.OPEN,
            "title": "Shared",
            "detail": "Shared test recommendation",
            "action": "Review",
            "first_seen": now,
            "last_seen": now,
        }
        Recommendation.objects.create(organization=self.org_a, **common)
        Recommendation.objects.create(organization=self.org_b, **common)
        self.assertEqual(Recommendation.objects.filter(source_key="shared-source-key").count(), 2)
