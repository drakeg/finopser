from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .account_models import OrganizationMembership
from .automation_models import RemediationAction
from .integration_models import IntegrationDelivery, IntegrationDestination, NotificationChannel
from .models import Organization
from .notification_producers import (
    dispatch_recommendation_open,
    recommendation_payload,
    recommendation_source_id,
)
from .recommendation_models import Recommendation
from .webhook_delivery import WebhookResponse


class RecommendationExternalNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="recommendation-external-owner", password="password123")
        self.organization = Organization.objects.create(name="Recommendation External Org")
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        now = timezone.now()
        self.recommendation = Recommendation.objects.create(
            organization=self.organization,
            source_key="cost-growth:ec2",
            source_type="cost_growth",
            category=Recommendation.Category.COST,
            priority=Recommendation.Priority.HIGH,
            status=Recommendation.Status.OPEN,
            title="Review EC2 cost growth",
            detail="Arbitrary detailed explanation that must not be sent.",
            action="Detailed action instructions that must not be sent.",
            estimated_monthly_savings=Decimal("42.50"),
            evidence={"secret_like_evidence": "do-not-send"},
            first_seen=now,
            last_seen=now,
        )
        self.destination = IntegrationDestination.objects.create(organization=self.organization, name="recommendation-hook", endpoint_url="http://localhost:9999/hook", signing_secret_digest="a" * 64, signing_secret_prefix="finopser_whsec_a", created_by=self.user)
        self.channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="recommendation-channel", event_types=["recommendation.open"], created_by=self.user)
        self.calls = []

    def transport(self, request):
        self.calls.append(request)
        return WebhookResponse(status_code=204)

    def secret_for(self, destination):
        self.assertEqual(destination.id, self.destination.id)
        return "finopser_whsec_recommendation-test"

    def test_open_recommendation_dispatch_is_metadata_only_deduplicated_and_side_effect_free(self):
        self.assertEqual(recommendation_source_id(self.recommendation), f"recommendation:{self.organization.id}:cost-growth:ec2")
        payload = recommendation_payload(self.recommendation)
        self.assertNotIn("evidence", payload)
        self.assertNotIn("detail", payload)
        self.assertNotIn("action", payload)
        first = dispatch_recommendation_open(self.recommendation, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        second = dispatch_recommendation_open(self.recommendation, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(IntegrationDelivery.objects.count(), 1)
        self.assertEqual(RemediationAction.objects.count(), 0)

    def test_non_open_unowned_disabled_and_unsubscribed_recommendations_fail_closed(self):
        for status in (Recommendation.Status.DISMISSED, Recommendation.Status.RESOLVED):
            self.recommendation.status = status
            self.assertEqual(dispatch_recommendation_open(self.recommendation, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.recommendation.status = Recommendation.Status.OPEN
        self.channel.event_types = ["report.ready"]
        self.channel.save(update_fields=["event_types"])
        self.assertEqual(dispatch_recommendation_open(self.recommendation, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.channel.event_types = ["recommendation.open"]
        self.channel.is_active = False
        self.channel.save(update_fields=["event_types", "is_active"])
        self.assertEqual(dispatch_recommendation_open(self.recommendation, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.assertEqual(self.calls, [])
