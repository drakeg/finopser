from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import CloudAccount, CloudResource, CostRecord, Organization, OrganizationNode, Project
from .rbac import AUDITOR, FINOPS_ANALYST
from .recommendation_models import Recommendation
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
