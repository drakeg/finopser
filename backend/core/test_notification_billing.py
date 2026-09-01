from django.test import TestCase, override_settings

from .account_models import Notification, Subscription
from .billing_api import _notify_billing_attention
from .models import Organization


@override_settings(NOTIFICATION_PROVIDER="disabled")
class BillingNotificationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Billing Notification Workspace")
        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan=Subscription.Plan.PRO,
            status=Subscription.Status.ACTIVE,
        )

    def test_past_due_and_canceled_states_create_deduplicated_attention(self):
        self.subscription.status = Subscription.Status.PAST_DUE
        self.subscription.save(update_fields=["status"])
        _notify_billing_attention(self.subscription)
        _notify_billing_attention(self.subscription)

        past_due = Notification.objects.get(
            organization=self.organization,
            dedupe_key=f"billing:subscription:{self.subscription.id}:past-due",
        )
        self.assertEqual(past_due.occurrence_count, 2)
        self.assertEqual(past_due.severity, Notification.Severity.HIGH)

        self.subscription.status = Subscription.Status.CANCELED
        self.subscription.save(update_fields=["status"])
        _notify_billing_attention(self.subscription)

        canceled = Notification.objects.get(
            organization=self.organization,
            dedupe_key=f"billing:subscription:{self.subscription.id}:canceled",
        )
        self.assertEqual(canceled.severity, Notification.Severity.WARNING)
        self.assertEqual(Notification.objects.filter(organization=self.organization).count(), 2)
