from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .account_models import OrganizationMembership
from .automation_models import RemediationAction, RemediationEvent
from .integration_models import IntegrationDelivery, IntegrationDestination, NotificationChannel
from .models import CloudAccount, CloudResource, Organization, OrganizationNode, Project
from .notification_producers import (
    dispatch_remediation_lifecycle,
    remediation_event_type,
    remediation_payload,
    remediation_source_id,
)
from .webhook_delivery import WebhookResponse


class RemediationExternalNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="remediation-external-owner", password="password123")
        self.organization = Organization.objects.create(name="Remediation External Org")
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        project = Project.objects.create(organization=self.organization, node=node, name="Default")
        self.account = CloudAccount.objects.create(organization=self.organization, project=project, name="AWS", provider_account_id="123456789012", role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly", status=CloudAccount.Status.VALID)
        self.resource = CloudResource.objects.create(provider="aws", cloud_account=self.account, provider_resource_id="ec2:123456789012:us-east-1:i-test", resource_type="aws.ec2.instance", name="i-test", region="us-east-1", state="running", is_active=True, last_seen=timezone.now(), metadata={})
        self.action = RemediationAction.objects.create(resource=self.resource, cloud_account=self.account, action_key="add_tags", status=RemediationAction.Status.PREVIEWED, simulation=True, parameters={"secret_like": "do-not-send"}, preview={"provider": "do-not-send"}, evidence_fingerprint="do-not-send", provider_result={"diagnostic": "do-not-send"}, error="do-not-send", requested_by=self.user)
        self.destination = IntegrationDestination.objects.create(organization=self.organization, name="remediation-hook", endpoint_url="http://localhost:9999/hook", signing_secret_digest="a" * 64, signing_secret_prefix="finopser_whsec_a", created_by=self.user)
        self.channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="remediation-channel", event_types=["remediation.approval_required", "remediation.completed"], created_by=self.user)
        self.calls = []

    def transport(self, request):
        self.calls.append(request)
        return WebhookResponse(status_code=204)

    def secret_for(self, destination):
        self.assertEqual(destination.id, self.destination.id)
        return "finopser_whsec_remediation-test"

    def test_approval_required_is_metadata_only_deduplicated_and_side_effect_free(self):
        self.assertEqual(remediation_event_type(self.action), "remediation.approval_required")
        self.assertEqual(remediation_source_id(self.action), f"remediation:{self.action.id}:previewed")
        payload = remediation_payload(self.action)
        for excluded in ("parameters", "preview", "provider_result", "error", "evidence_fingerprint"):
            self.assertNotIn(excluded, payload)
        original_updated_at = self.action.updated_at
        first = dispatch_remediation_lifecycle(self.action, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        second = dispatch_remediation_lifecycle(self.action, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        self.action.refresh_from_db()
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(IntegrationDelivery.objects.count(), 1)
        self.assertEqual(RemediationEvent.objects.count(), 0)
        self.assertEqual(self.action.status, RemediationAction.Status.PREVIEWED)
        self.assertEqual(self.action.updated_at, original_updated_at)

    def test_terminal_states_are_distinct_and_ineligible_states_fail_closed(self):
        for status in (RemediationAction.Status.SUCCEEDED, RemediationAction.Status.FAILED, RemediationAction.Status.STALE, RemediationAction.Status.REJECTED):
            self.action.status = status
            self.assertEqual(remediation_event_type(self.action), "remediation.completed")
            deliveries = dispatch_remediation_lifecycle(self.action, signing_secret_for=self.secret_for, transport=self.transport)
            self.assertEqual(deliveries[0].event_type, "remediation.completed")
        self.assertEqual(IntegrationDelivery.objects.count(), 4)
        for status in (RemediationAction.Status.REQUESTED, RemediationAction.Status.APPROVED):
            self.action.status = status
            self.assertEqual(dispatch_remediation_lifecycle(self.action, signing_secret_for=self.secret_for, transport=self.transport), [])
