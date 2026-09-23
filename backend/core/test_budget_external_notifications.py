from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .account_models import OrganizationMembership
from .budgets import budget_snapshot
from .integration_models import (
    IntegrationDelivery,
    IntegrationDestination,
    NotificationChannel,
)
from .models import (
    Budget,
    CloudAccount,
    CostRecord,
    Organization,
    OrganizationNode,
    Project,
)
from .notification_producers import (
    budget_threshold_payload,
    budget_threshold_source_id,
    dispatch_budget_threshold,
)
from .webhook_delivery import WebhookResponse


class BudgetExternalNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budget-external-owner", password="password123")
        self.organization = Organization.objects.create(name="Budget External Org")
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        project = Project.objects.create(organization=self.organization, node=node, name="Default")
        self.account = CloudAccount.objects.create(organization=self.organization, project=project, name="AWS", provider_account_id="123456789012", role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly", status=CloudAccount.Status.VALID)
        self.budget = Budget.objects.create(organization=self.organization, name="Monthly cloud budget", amount=Decimal("100.00"), warning_threshold=Decimal("80"), critical_threshold=Decimal("90"))
        CostRecord.objects.create(provider="aws", cloud_account=self.account, project=project, provider_account_id=self.account.provider_account_id, usage_date=date(2026, 8, 20), service="AmazonEC2", region="us-east-1", amount=Decimal("120.00"), currency="USD", updated_at=timezone.now())
        self.destination = IntegrationDestination.objects.create(organization=self.organization, name="budget-hook", endpoint_url="http://localhost:9999/hook", signing_secret_digest="a" * 64, signing_secret_prefix="finopser_whsec_a", created_by=self.user)
        self.channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="budget-channel", event_types=["cost.threshold"], created_by=self.user)
        self.calls = []

    def transport(self, request):
        self.calls.append(request)
        return WebhookResponse(status_code=204)

    def secret_for(self, destination):
        self.assertEqual(destination.id, self.destination.id)
        return "finopser_whsec_budget-test"

    def test_budget_threshold_dispatch_is_stable_deduplicated_and_sanitized(self):
        snapshot = budget_snapshot(self.budget, today=date(2026, 8, 20))
        self.assertEqual(budget_threshold_source_id(self.budget, snapshot), f"budget:{self.budget.id}:2026-08-01:exceeded")
        payload = budget_threshold_payload(self.budget, snapshot)
        self.assertEqual(payload["level"], "exceeded")
        self.assertNotIn("signing_secret", payload)
        first = dispatch_budget_threshold(self.budget, snapshot, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        second = dispatch_budget_threshold(self.budget, snapshot, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(IntegrationDelivery.objects.count(), 1)

    def test_disabled_or_unsubscribed_channel_does_not_dispatch(self):
        snapshot = budget_snapshot(self.budget, today=date(2026, 8, 20))
        self.channel.event_types = ["report.ready"]
        self.channel.save(update_fields=["event_types"])
        self.assertEqual(dispatch_budget_threshold(self.budget, snapshot, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.channel.event_types = ["cost.threshold"]
        self.channel.is_active = False
        self.channel.save(update_fields=["event_types", "is_active"])
        self.assertEqual(dispatch_budget_threshold(self.budget, snapshot, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.assertEqual(self.calls, [])
