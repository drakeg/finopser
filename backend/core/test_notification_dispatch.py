from django.contrib.auth.models import User
from django.test import TestCase

from .account_models import OrganizationMembership
from .integration_models import IntegrationDelivery, IntegrationDestination, NotificationChannel
from .models import AuditEvent, Organization
from .notification_dispatch import dispatch_notification_event
from .webhook_delivery import WebhookResponse


class NotificationDispatchTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Dispatch Tenant")
        self.manager = User.objects.create_user(username="dispatch-manager", password="test-password-long")
        OrganizationMembership.objects.create(user=self.manager, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        self.destination = IntegrationDestination.objects.create(organization=self.organization, name="dispatch-hook", endpoint_url="http://localhost:9999/hook", signing_secret_digest="a" * 64, signing_secret_prefix="finopser_whsec_a", created_by=self.manager)
        self.channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="cost-and-governance", event_types=["cost.threshold", "governance.finding"], created_by=self.manager)
        self.calls = []

    def transport(self, request):
        self.calls.append(request)
        return WebhookResponse(status_code=204)

    def secret_for(self, destination):
        self.assertEqual(destination.id, self.destination.id)
        return "finopser_whsec_dispatch-test"

    def test_subscribed_event_delivers_once_and_is_deduplicated(self):
        first = dispatch_notification_event(self.organization, "cost.threshold", "budget-42", {"budget_id": 42}, self.secret_for, self.transport, actor=self.manager)
        second = dispatch_notification_event(self.organization, "cost.threshold", "budget-42", {"budget_id": 42}, self.secret_for, self.transport, actor=self.manager)
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(IntegrationDelivery.objects.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="notification_channel.dispatch").exists())

    def test_unsubscribed_disabled_channel_or_destination_do_not_deliver(self):
        self.assertEqual(dispatch_notification_event(self.organization, "report.ready", "report-1", {}, self.secret_for, self.transport), [])
        self.channel.is_active = False
        self.channel.save(update_fields=["is_active"])
        self.assertEqual(dispatch_notification_event(self.organization, "cost.threshold", "budget-1", {}, self.secret_for, self.transport), [])
        self.channel.is_active = True
        self.channel.save(update_fields=["is_active"])
        self.destination.is_active = False
        self.destination.save(update_fields=["is_active"])
        self.assertEqual(dispatch_notification_event(self.organization, "cost.threshold", "budget-2", {}, self.secret_for, self.transport), [])
        self.assertEqual(self.calls, [])

    def test_tenant_isolation_and_unknown_event_fail_closed(self):
        other = Organization.objects.create(name="Other Dispatch Tenant")
        self.assertEqual(dispatch_notification_event(other, "cost.threshold", "budget-1", {}, self.secret_for, self.transport), [])
        with self.assertRaisesRegex(ValueError, "Unsupported notification event type"):
            dispatch_notification_event(self.organization, "unknown.event", "source", {}, self.secret_for, self.transport)
        self.assertEqual(self.calls, [])
