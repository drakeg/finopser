from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .account_models import Notification, OrganizationMembership
from .budgets import evaluate_budgets
from .compliance import evaluate_compliance
from .models import (
    Budget,
    CloudAccount,
    CloudResource,
    CostRecord,
    Organization,
    OrganizationNode,
    Project,
)
from .policies import evaluate_policies
from .recommendations import generate_recommendations


class NotificationSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="signal-owner", password="password123")
        self.organization = Organization.objects.create(name="Signal Org")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        project = Project.objects.create(
            organization=self.organization,
            node=node,
            name="Default",
        )
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            project=project,
            name="AWS",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )
        self.resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id="ec2:123456789012:us-east-1:i-public",
            resource_type="aws.ec2.instance",
            name="i-public",
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={"public_ip_address": "203.0.113.10"},
        )

    def test_budget_threshold_generates_deduplicated_notification(self):
        budget = Budget.objects.create(
            organization=self.organization,
            name="Monthly cloud budget",
            amount=Decimal("100.00"),
            warning_threshold=Decimal("80"),
            critical_threshold=Decimal("90"),
        )
        CostRecord.objects.create(
            provider="aws",
            cloud_account=self.account,
            project=self.account.project,
            provider_account_id=self.account.provider_account_id,
            usage_date=date(2026, 8, 20),
            service="AmazonEC2",
            region="us-east-1",
            amount=Decimal("120.00"),
            currency="USD",
            updated_at=timezone.now(),
        )

        evaluate_budgets(self.user, today=date(2026, 8, 20))
        evaluate_budgets(self.user, today=date(2026, 8, 20))

        notification = Notification.objects.get(
            organization=self.organization,
            dedupe_key=f"budget:{budget.id}:2026-08-01:exceeded",
        )
        self.assertEqual(notification.category, "budget")
        self.assertEqual(notification.severity, "critical")
        self.assertEqual(notification.occurrence_count, 2)

    def test_compliance_failure_generates_single_coalesced_notification(self):
        evaluate_compliance(self.user)
        evaluate_compliance(self.user)

        notification = Notification.objects.get(
            organization=self.organization,
            dedupe_key="compliance:open-failures",
        )
        self.assertEqual(notification.category, "compliance")
        self.assertEqual(notification.severity, "high")
        self.assertEqual(notification.occurrence_count, 2)
        self.assertEqual(Notification.objects.filter(category="compliance").count(), 1)

    def test_policy_violation_generates_single_coalesced_notification(self):
        evaluate_policies(self.user)
        evaluate_policies(self.user)

        notification = Notification.objects.get(
            organization=self.organization,
            dedupe_key="policy:open-violations",
        )
        self.assertEqual(notification.category, "policy")
        self.assertEqual(notification.severity, "high")
        self.assertEqual(notification.occurrence_count, 2)
        self.assertEqual(Notification.objects.filter(category="policy").count(), 1)

    def test_recommendation_generation_creates_actionable_coalesced_notification(self):
        generate_recommendations(self.user, today=date(2026, 8, 20))
        generate_recommendations(self.user, today=date(2026, 8, 20))

        notification = Notification.objects.get(
            organization=self.organization,
            dedupe_key=f"recommendation:untagged-resource:{self.resource.id}",
        )
        self.assertEqual(notification.category, "recommendation")
        self.assertEqual(notification.severity, "low")
        self.assertEqual(notification.target, "Recommendations")
        self.assertEqual(notification.object_type, "recommendation")
        self.assertEqual(notification.occurrence_count, 2)
