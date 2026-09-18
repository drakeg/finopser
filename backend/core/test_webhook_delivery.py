import hashlib
import hmac
import json

from django.contrib.auth.models import User
from django.test import TestCase

from .account_models import OrganizationMembership
from .integration_models import IntegrationDelivery, IntegrationDestination
from .models import Organization
from .webhook_delivery import WebhookResponse, build_webhook_request, deliver_webhook


class SignedWebhookDeliveryTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Webhook Delivery Tenant")
        self.owner = User.objects.create_user(username="webhook-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.destination = IntegrationDestination.objects.create(
            organization=self.organization,
            name="events",
            endpoint_url="http://localhost:9999/events",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="finopser_whsec_a",
            created_by=self.owner,
        )
        self.secret = "finopser_whsec_test-secret"

    def test_request_signature_is_verifiable_and_deterministic(self):
        request = build_webhook_request(
            self.destination,
            "governance.finding",
            {"finding_id": "f-1", "severity": "high"},
            self.secret,
            event_id="evt-1",
            timestamp=1234567890,
        )
        expected = hmac.new(
            self.secret.encode(),
            b"1234567890." + request.body,
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(request.headers["X-Finopser-Signature"], f"v1={expected}")
        self.assertEqual(json.loads(request.body)["event_id"], "evt-1")

    def test_successful_delivery_records_sanitized_history(self):
        seen = []
        delivery = deliver_webhook(
            self.destination,
            "report.ready",
            {"report_id": "r-1"},
            self.secret,
            lambda request: seen.append(request) or WebhookResponse(204),
        )
        self.assertEqual(delivery.status, IntegrationDelivery.Status.SUCCEEDED)
        self.assertEqual(delivery.attempt_count, 1)
        self.assertEqual(delivery.response_status, 204)
        self.assertNotIn(self.secret, str(delivery.__dict__))
        self.assertEqual(len(seen), 1)

    def test_failures_retry_at_most_three_times(self):
        attempts = []
        delivery = deliver_webhook(
            self.destination,
            "report.ready",
            {"report_id": "r-2"},
            self.secret,
            lambda request: attempts.append(request) or WebhookResponse(503),
        )
        self.assertEqual(delivery.status, IntegrationDelivery.Status.FAILED)
        self.assertEqual(delivery.attempt_count, 3)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(delivery.last_error, "HTTP 503")

    def test_disabled_destination_fails_before_transport(self):
        self.destination.is_active = False
        self.destination.save(update_fields=["is_active"])
        called = []
        with self.assertRaisesMessage(ValueError, "disabled"):
            deliver_webhook(
                self.destination,
                "report.ready",
                {},
                self.secret,
                lambda request: called.append(request),
            )
        self.assertEqual(called, [])
        self.assertFalse(IntegrationDelivery.objects.exists())

    def test_unsupported_event_fails_closed(self):
        with self.assertRaisesMessage(ValueError, "Unsupported"):
            build_webhook_request(self.destination, "resource.delete", {}, self.secret)

    def test_transport_exception_is_sanitized(self):
        def failing_transport(_request):
            raise RuntimeError("secret provider diagnostic")

        delivery = deliver_webhook(
            self.destination,
            "report.ready",
            {},
            self.secret,
            failing_transport,
        )
        self.assertEqual(delivery.status, IntegrationDelivery.Status.FAILED)
        self.assertEqual(delivery.last_error, "RuntimeError")
        self.assertNotIn("provider diagnostic", delivery.last_error)
