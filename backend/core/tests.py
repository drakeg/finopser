from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group, User
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APITestCase

from .models import AuditEvent, CloudAccount, Organization, OrganizationNode, Project
from .providers.aws import AWSProvider
from .providers.base import ProviderValidationError, ValidationResult
from .rbac import AUDITOR, CLOUD_ADMIN, PLATFORM_ADMIN


class FoundationEndpointTests(SimpleTestCase):
    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_session_is_anonymous_by_default(self):
        response = self.client.get("/api/auth/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "username": None})

    def test_request_id_is_added(self):
        response = self.client.get("/api/health/", HTTP_X_REQUEST_ID="test-request-id")
        self.assertEqual(response["X-Request-ID"], "test-request-id")


class ReadinessIntegrationTests(TestCase):
    def test_readiness_checks_required_dependencies(self):
        response = self.client.get("/api/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"], {"database": "ok", "redis": "ok"})


class AWSProviderTests(SimpleTestCase):
    @patch("core.providers.aws.boto3.client")
    def test_assume_role_and_identity_validation(self, client_mock):
        source_sts = MagicMock()
        assumed_sts = MagicMock()
        source_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "temporary-key",
                "SecretAccessKey": "temporary-secret",
                "SessionToken": "temporary-token",
            }
        }
        assumed_sts.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/Finopser/validation",
            "UserId": "AROATEST:validation",
        }
        client_mock.side_effect = [source_sts, assumed_sts]

        result = AWSProvider().validate_account(
            account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            external_id="test-external-id",
        )

        self.assertEqual(result.provider_account_id, "123456789012")
        source_sts.assume_role.assert_called_once()
        self.assertEqual(client_mock.call_count, 2)

    @patch("core.providers.aws.boto3.client")
    def test_identity_mismatch_is_rejected(self, client_mock):
        source_sts = MagicMock()
        assumed_sts = MagicMock()
        source_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "temporary-key",
                "SecretAccessKey": "temporary-secret",
                "SessionToken": "temporary-token",
            }
        }
        assumed_sts.get_caller_identity.return_value = {
            "Account": "999999999999",
            "Arn": "arn:aws:sts::999999999999:assumed-role/Finopser/validation",
            "UserId": "AROATEST:validation",
        }
        client_mock.side_effect = [source_sts, assumed_sts]

        with self.assertRaises(ProviderValidationError):
            AWSProvider().validate_account(
                account_id="123456789012",
                role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            )


class GovernanceApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="password")
        Group.objects.get_or_create(name=PLATFORM_ADMIN)[0].user_set.add(self.admin)
        self.viewer = User.objects.create_user(username="auditor", password="password")
        Group.objects.get_or_create(name=AUDITOR)[0].user_set.add(self.viewer)

    def test_unauthenticated_organization_list_is_denied(self):
        response = self.client.get("/api/organizations/")
        self.assertIn(response.status_code, (401, 403))

    def test_admin_can_create_hierarchy_and_project_with_audit_events(self):
        self.client.force_authenticate(self.admin)
        org_response = self.client.post("/api/organizations/", {"name": "Acme"}, format="json")
        self.assertEqual(org_response.status_code, 201)
        org_id = org_response.data["id"]
        root_response = self.client.post("/api/organization-nodes/", {"organization": org_id, "name": "Engineering", "node_type": "department"}, format="json")
        self.assertEqual(root_response.status_code, 201)
        node_id = root_response.data["id"]
        project_response = self.client.post("/api/projects/", {"organization": org_id, "node": node_id, "name": "Platform"}, format="json")
        self.assertEqual(project_response.status_code, 201)
        self.assertEqual(AuditEvent.objects.filter(actor=self.admin).count(), 3)

    def test_auditor_is_read_only(self):
        org = Organization.objects.create(name="Acme")
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get("/api/organizations/").status_code, 200)
        self.assertEqual(self.client.patch(f"/api/organizations/{org.id}/", {"name": "Nope"}, format="json").status_code, 403)

    def test_node_parent_must_be_same_organization(self):
        self.client.force_authenticate(self.admin)
        org1 = Organization.objects.create(name="One")
        org2 = Organization.objects.create(name="Two")
        parent = OrganizationNode.objects.create(organization=org1, name="Parent")
        response = self.client.post("/api/organization-nodes/", {"organization": org2.id, "parent": parent.id, "name": "Child"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_node_cycles_are_rejected(self):
        self.client.force_authenticate(self.admin)
        org = Organization.objects.create(name="Cycle")
        parent = OrganizationNode.objects.create(organization=org, name="Parent")
        child = OrganizationNode.objects.create(organization=org, parent=parent, name="Child")
        response = self.client.patch(f"/api/organization-nodes/{parent.id}/", {"parent": child.id}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cloud_admin_can_manage_organizations(self):
        cloud_admin = User.objects.create_user(username="cloud", password="password")
        Group.objects.get_or_create(name=CLOUD_ADMIN)[0].user_set.add(cloud_admin)
        self.client.force_authenticate(cloud_admin)
        self.assertEqual(self.client.post("/api/organizations/", {"name": "Managed"}, format="json").status_code, 201)

    def test_platform_admin_can_assign_managed_roles(self):
        target = User.objects.create_user(username="target")
        self.client.force_authenticate(self.admin)
        response = self.client.put(f"/api/users/{target.id}/roles/", {"roles": [CLOUD_ADMIN]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn(CLOUD_ADMIN, response.data["roles"])
        self.assertTrue(AuditEvent.objects.filter(action="update_roles", object_id=str(target.id)).exists())

    def _create_project(self, org_name="AWS Org"):
        org = Organization.objects.create(name=org_name)
        node = OrganizationNode.objects.create(organization=org, name="Cloud")
        project = Project.objects.create(organization=org, node=node, name="AWS Project")
        return org, project

    def test_aws_account_registration_rejects_long_lived_keys(self):
        org, project = self._create_project()
        self.client.force_authenticate(self.admin)
        payload = {
            "provider": "aws",
            "organization": org.id,
            "project": project.id,
            "name": "Production",
            "provider_account_id": "123456789012",
            "role_arn": "arn:aws:iam::123456789012:role/FinopserReadOnly",
            "aws_access_key_id": "must-not-be-accepted",
        }
        response = self.client.post("/api/cloud-accounts/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CloudAccount.objects.exists())

    def test_cloud_account_project_must_match_organization(self):
        org1, _ = self._create_project("Org One")
        _, project2 = self._create_project("Org Two")
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/cloud-accounts/",
            {
                "provider": "aws",
                "organization": org1.id,
                "project": project2.id,
                "name": "Invalid",
                "provider_account_id": "123456789012",
                "role_arn": "arn:aws:iam::123456789012:role/FinopserReadOnly",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("core.api.get_provider")
    def test_cloud_account_validation_persists_safe_status_and_audit(self, provider_factory):
        org, project = self._create_project()
        account = CloudAccount.objects.create(
            organization=org,
            project=project,
            name="Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            external_id="write-only-value",
        )
        provider = MagicMock()
        provider.validate_account.return_value = ValidationResult(
            provider_account_id="123456789012",
            arn="arn:aws:sts::123456789012:assumed-role/Finopser/validation",
            metadata={"user_id": "AROATEST:validation"},
        )
        provider_factory.return_value = provider
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/cloud-accounts/{account.id}/validate/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], CloudAccount.Status.VALID)
        self.assertNotIn("external_id", response.data)
        self.assertTrue(AuditEvent.objects.filter(action="validate_success").exists())
