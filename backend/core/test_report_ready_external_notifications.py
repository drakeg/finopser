from django.contrib.auth.models import User
from django.test import TestCase

from .account_models import OrganizationMembership
from .integration_models import IntegrationDelivery, IntegrationDestination, NotificationChannel
from .models import Organization
from .notification_producers import dispatch_report_ready, report_ready_payload
from .reporting import build_audit_events_report
from .webhook_delivery import WebhookResponse


class ReportReadyExternalNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="report-external-owner", password="password123")
        self.organization = Organization.objects.create(name="Report External Org")
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        self.destination = IntegrationDestination.objects.create(organization=self.organization, name="report-hook", endpoint_url="http://localhost:9999/hook", signing_secret_digest="a" * 64, signing_secret_prefix="finopser_whsec_a", created_by=self.user)
        self.channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="report-channel", event_types=["report.ready"], created_by=self.user)
        self.calls = []

    def transport(self, request):
        self.calls.append(request)
        return WebhookResponse(status_code=204)

    def secret_for(self, destination):
        self.assertEqual(destination.id, self.destination.id)
        return "finopser_whsec_report-test"

    def test_report_ready_dispatch_deduplicates_and_never_exposes_content(self):
        result = build_audit_events_report(self.user)
        payload = report_ready_payload(result)
        self.assertEqual(payload["report_code"], "audit-events")
        self.assertNotIn("content", payload)
        first = dispatch_report_ready(self.organization, result, "report-generation-42", signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        second = dispatch_report_ready(self.organization, result, "report-generation-42", signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(IntegrationDelivery.objects.count(), 1)

    def test_invalid_disabled_and_unsubscribed_report_dispatch_fails_closed(self):
        result = build_audit_events_report(self.user)
        with self.assertRaisesRegex(ValueError, "source id"):
            dispatch_report_ready(self.organization, result, " ", signing_secret_for=self.secret_for, transport=self.transport)
        self.channel.event_types = ["cost.threshold"]
        self.channel.save(update_fields=["event_types"])
        self.assertEqual(dispatch_report_ready(self.organization, result, "report-1", signing_secret_for=self.secret_for, transport=self.transport), [])
        self.channel.event_types = ["report.ready"]
        self.channel.is_active = False
        self.channel.save(update_fields=["event_types", "is_active"])
        self.assertEqual(dispatch_report_ready(self.organization, result, "report-2", signing_secret_for=self.secret_for, transport=self.transport), [])
        self.assertEqual(self.calls, [])
