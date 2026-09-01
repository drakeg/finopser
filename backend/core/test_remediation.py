from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .account_models import Notification
from .automation_models import RemediationAction, RemediationEvent
from .models import CloudAccount, CloudResource, Organization, OrganizationNode, Project
from .rbac import CLOUD_ADMIN, FINOPS_ANALYST, PLATFORM_ADMIN
from .remediation import ACTION_ADD_TAGS


class RemediationWorkflowTests(APITestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="finops-remediation", password="password")
        Group.objects.get_or_create(name=FINOPS_ANALYST)[0].user_set.add(self.requester)
        self.admin = User.objects.create_user(username="platform-remediation", password="password")
        Group.objects.get_or_create(name=PLATFORM_ADMIN)[0].user_set.add(self.admin)
        self.cloud_admin = User.objects.create_user(username="cloud-remediation", password="password")
        Group.objects.get_or_create(name=CLOUD_ADMIN)[0].user_set.add(self.cloud_admin)
        self.org = Organization.objects.create(name="Automation Org")
        self.node = OrganizationNode.objects.create(organization=self.org, name="Platform")
        self.project = Project.objects.create(organization=self.org, node=self.node, name="Core")
        self.account = CloudAccount.objects.create(
            organization=self.org,
            project=self.project,
            name="Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserAutomation",
            external_id="test-external-id",
            status=CloudAccount.Status.VALID,
        )
        self.resource = CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id="ec2:123456789012:us-east-1:i-0123456789abcdef0",
            resource_type="aws.ec2.instance",
            name="web-1",
            region="us-east-1",
            state="running",
            is_active=True,
            last_seen=timezone.now(),
            metadata={"instance_type": "t3.small"},
            tags={"Name": "web-1"},
        )

    def create_action(self, *, simulation=True):
        self.client.force_authenticate(self.requester)
        response = self.client.post(
            "/api/remediations/",
            {
                "resource": self.resource.id,
                "cloud_account": self.account.id,
                "action_key": ACTION_ADD_TAGS,
                "simulation": simulation,
                "parameters": {"tags": {"Owner": "platform", "CostCenter": "1234"}},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return RemediationAction.objects.get(pk=response.data["id"])

    @patch("core.providers.aws.boto3.client")
    def test_preview_never_calls_provider(self, boto_client):
        action = self.create_action()
        response = self.client.post(f"/api/remediations/{action.id}/preview/")
        self.assertEqual(response.status_code, 200)
        action.refresh_from_db()
        self.assertEqual(action.status, RemediationAction.Status.PREVIEWED)
        self.assertFalse(action.preview["provider_mutation"])
        self.assertEqual(action.preview["changes"]["Owner"]["to"], "platform")
        notification = Notification.objects.get(
            organization=self.org,
            dedupe_key=f"remediation:{action.id}:approval",
        )
        self.assertEqual(notification.severity, "warning")
        self.assertEqual(notification.target, "Automation")
        self.assertEqual(notification.object_id, str(action.id))
        boto_client.assert_not_called()

    @patch("core.providers.aws.boto3.client")
    def test_simulation_requires_approval_and_never_calls_provider(self, boto_client):
        action = self.create_action(simulation=True)
        self.client.post(f"/api/remediations/{action.id}/preview/")
        denied = self.client.post(f"/api/remediations/{action.id}/execute/")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.admin)
        approved = self.client.post(f"/api/remediations/{action.id}/approve/")
        self.assertEqual(approved.status_code, 200)
        executed = self.client.post(f"/api/remediations/{action.id}/execute/")
        self.assertEqual(executed.status_code, 200)
        action.refresh_from_db()
        self.assertEqual(action.status, RemediationAction.Status.SUCCEEDED)
        self.assertTrue(action.provider_result["simulation"])
        self.assertFalse(action.provider_result["mutated"])
        notification = Notification.objects.get(
            organization=self.org,
            dedupe_key=f"remediation:{action.id}:succeeded",
        )
        self.assertEqual(notification.severity, "info")
        self.assertIn("simulation", notification.detail.lower())
        boto_client.assert_not_called()
        self.assertTrue(RemediationEvent.objects.filter(action=action, event_type="approved").exists())
        self.assertTrue(RemediationEvent.objects.filter(action=action, event_type="executed").exists())

    def test_stale_evidence_blocks_execution(self):
        action = self.create_action()
        self.client.post(f"/api/remediations/{action.id}/preview/")
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/remediations/{action.id}/approve/")
        self.resource.tags = {"Name": "web-1", "Changed": "outside-finopser"}
        self.resource.save(update_fields=["tags"])
        response = self.client.post(f"/api/remediations/{action.id}/execute/")
        self.assertEqual(response.status_code, 409)
        action.refresh_from_db()
        self.assertEqual(action.status, RemediationAction.Status.STALE)
        self.assertIn("changed after preview", action.error)
        notification = Notification.objects.get(
            organization=self.org,
            dedupe_key=f"remediation:{action.id}:stale",
        )
        self.assertEqual(notification.severity, "high")
        self.assertEqual(notification.target, "Automation")

    @patch("core.remediation.AWSProvider._assumed_session")
    def test_real_ec2_tag_execution_uses_allowlisted_api(self, assumed_session):
        ec2 = MagicMock()
        session = MagicMock()
        session.client.return_value = ec2
        assumed_session.return_value = session
        action = self.create_action(simulation=False)
        self.client.post(f"/api/remediations/{action.id}/preview/")
        self.client.force_authenticate(self.cloud_admin)
        self.client.post(f"/api/remediations/{action.id}/approve/")
        response = self.client.post(f"/api/remediations/{action.id}/execute/")
        self.assertEqual(response.status_code, 200)
        ec2.create_tags.assert_called_once_with(
            Resources=["i-0123456789abcdef0"],
            Tags=[
                {"Key": "CostCenter", "Value": "1234"},
                {"Key": "Owner", "Value": "platform"},
            ],
        )
        action.refresh_from_db()
        self.resource.refresh_from_db()
        self.assertEqual(action.status, RemediationAction.Status.SUCCEEDED)
        self.assertEqual(self.resource.tags["Owner"], "platform")

    @patch("core.remediation.AWSProvider._assumed_session")
    def test_provider_failure_generates_critical_notification(self, assumed_session):
        session = MagicMock()
        session.client.side_effect = KeyError("provider unavailable")
        assumed_session.return_value = session
        action = self.create_action(simulation=False)
        self.client.post(f"/api/remediations/{action.id}/preview/")
        self.client.force_authenticate(self.cloud_admin)
        self.client.post(f"/api/remediations/{action.id}/approve/")

        response = self.client.post(f"/api/remediations/{action.id}/execute/")

        self.assertEqual(response.status_code, 400)
        notification = Notification.objects.get(
            organization=self.org,
            dedupe_key=f"remediation:{action.id}:failed",
        )
        self.assertEqual(notification.severity, "critical")
        self.assertIn("provider unavailable", notification.detail)

    def test_reserved_tag_keys_and_unsupported_resources_are_rejected_at_preview(self):
        self.client.force_authenticate(self.requester)
        response = self.client.post(
            "/api/remediations/",
            {
                "resource": self.resource.id,
                "cloud_account": self.account.id,
                "action_key": ACTION_ADD_TAGS,
                "parameters": {"tags": {"aws:reserved": "no"}},
            },
            format="json",
        )
        action = RemediationAction.objects.get(pk=response.data["id"])
        preview = self.client.post(f"/api/remediations/{action.id}/preview/")
        self.assertEqual(preview.status_code, 400)

        bucket = CloudResource.objects.create(
            provider="aws",
            cloud_account=self.account,
            provider_resource_id="arn:aws:s3:::example-bucket",
            resource_type="aws.s3.bucket",
            name="example-bucket",
            region="global",
            state="available",
            is_active=True,
            last_seen=timezone.now(),
            tags={},
        )
        response = self.client.post(
            "/api/remediations/",
            {
                "resource": bucket.id,
                "cloud_account": self.account.id,
                "action_key": ACTION_ADD_TAGS,
                "parameters": {"tags": {"Owner": "platform"}},
            },
            format="json",
        )
        bucket_action = RemediationAction.objects.get(pk=response.data["id"])
        preview = self.client.post(f"/api/remediations/{bucket_action.id}/preview/")
        self.assertEqual(preview.status_code, 400)

    def test_non_manager_cannot_approve(self):
        action = self.create_action()
        self.client.post(f"/api/remediations/{action.id}/preview/")
        response = self.client.post(f"/api/remediations/{action.id}/approve/")
        self.assertEqual(response.status_code, 403)
