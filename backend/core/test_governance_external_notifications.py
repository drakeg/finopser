from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .account_models import OrganizationMembership
from .integration_models import IntegrationDelivery, IntegrationDestination, NotificationChannel
from .models import (
    CloudAccount,
    CloudResource,
    ComplianceControl,
    ComplianceFinding,
    ComplianceFramework,
    Organization,
    OrganizationNode,
    Project,
)
from .notification_producers import (
    dispatch_governance_finding,
    governance_finding_payload,
    governance_finding_source_id,
)
from .webhook_delivery import WebhookResponse


class GovernanceExternalNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="governance-external-owner", password="password123")
        self.organization = Organization.objects.create(name="Governance External Org")
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.OWNER)
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        project = Project.objects.create(organization=self.organization, node=node, name="Default")
        self.account = CloudAccount.objects.create(organization=self.organization, project=project, name="AWS", provider_account_id="123456789012", role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly", status=CloudAccount.Status.VALID)
        self.resource = CloudResource.objects.create(provider="aws", cloud_account=self.account, provider_resource_id="ec2:123456789012:us-east-1:i-public", resource_type="aws.ec2.instance", name="i-public", region="us-east-1", state="running", is_active=True, last_seen=timezone.now(), metadata={"public_ip_address": "203.0.113.10", "secret_like_evidence": "do-not-send"})
        framework = ComplianceFramework.objects.create(code="TEST", name="Test")
        control = ComplianceControl.objects.create(framework=framework, code="EC2-001", title="No public IPv4", severity=ComplianceControl.Severity.HIGH, resource_type="aws.ec2.instance", check_key="ec2_public_ipv4")
        now = timezone.now()
        self.finding = ComplianceFinding.objects.create(control=control, resource=self.resource, cloud_account=self.account, severity=ComplianceControl.Severity.HIGH, status=ComplianceFinding.Status.OPEN, evidence={"public_ip_address": "203.0.113.10", "secret_like_evidence": "do-not-send"}, first_seen=now, last_seen=now)
        self.destination = IntegrationDestination.objects.create(organization=self.organization, name="governance-hook", endpoint_url="http://localhost:9999/hook", signing_secret_digest="a" * 64, signing_secret_prefix="finopser_whsec_a", created_by=self.user)
        self.channel = NotificationChannel.objects.create(organization=self.organization, destination=self.destination, name="governance-channel", event_types=["governance.finding"], created_by=self.user)
        self.calls = []

    def transport(self, request):
        self.calls.append(request)
        return WebhookResponse(status_code=204)

    def secret_for(self, destination):
        self.assertEqual(destination.id, self.destination.id)
        return "finopser_whsec_governance-test"

    def test_open_finding_dispatch_is_stable_deduplicated_and_excludes_evidence(self):
        self.assertEqual(governance_finding_source_id(self.finding), f"compliance-finding:{self.finding.id}")
        payload = governance_finding_payload(self.finding)
        self.assertEqual(payload["control_code"], "EC2-001")
        self.assertNotIn("evidence", payload)
        self.assertNotIn("secret_like_evidence", payload)
        first = dispatch_governance_finding(self.finding, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        second = dispatch_governance_finding(self.finding, signing_secret_for=self.secret_for, transport=self.transport, actor=self.user)
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(IntegrationDelivery.objects.count(), 1)

    def test_resolved_excepted_disabled_and_unsubscribed_findings_do_not_dispatch(self):
        for status in (ComplianceFinding.Status.RESOLVED, ComplianceFinding.Status.EXCEPTED):
            self.finding.status = status
            self.assertEqual(dispatch_governance_finding(self.finding, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.finding.status = ComplianceFinding.Status.OPEN
        self.channel.event_types = ["report.ready"]
        self.channel.save(update_fields=["event_types"])
        self.assertEqual(dispatch_governance_finding(self.finding, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.channel.event_types = ["governance.finding"]
        self.channel.is_active = False
        self.channel.save(update_fields=["event_types", "is_active"])
        self.assertEqual(dispatch_governance_finding(self.finding, signing_secret_for=self.secret_for, transport=self.transport), [])
        self.assertEqual(self.calls, [])
