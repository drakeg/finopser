from django.contrib.auth.models import Group, User
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APITestCase

from .models import AuditEvent, Organization, OrganizationNode
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
