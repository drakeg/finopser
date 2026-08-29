from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .account_models import OrganizationMembership, Subscription
from .audit import record_audit
from .models import AuditEvent, CloudAccount, Organization, OrganizationNode, Project


class AuditAndCoreTenantIsolationTests(APITestCase):
    def _workspace(self, suffix):
        user = User.objects.create_user(username=f"audit-owner-{suffix}", password="password")
        organization = Organization.objects.create(name=f"Audit Tenant {suffix}")
        node = OrganizationNode.objects.create(organization=organization, name="Root")
        project = Project.objects.create(organization=organization, node=node, name="Default")
        account = CloudAccount.objects.create(
            organization=organization,
            project=project,
            name=f"Account {suffix}",
            provider_account_id=f"{int(suffix):012d}",
            role_arn=f"arn:aws:iam::{int(suffix):012d}:role/FinopserReadOnly",
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        Subscription.objects.create(
            organization=organization,
            plan=Subscription.Plan.BUSINESS,
            status=Subscription.Status.ACTIVE,
        )
        return user, organization, node, project, account

    def setUp(self):
        self.user_a, self.org_a, self.node_a, self.project_a, self.account_a = self._workspace("301")
        self.user_b, self.org_b, self.node_b, self.project_b, self.account_b = self._workspace("302")
        self.client.force_authenticate(self.user_a)

    def test_audit_events_record_workspace_ownership_and_do_not_leak(self):
        own_event = record_audit(self.user_a, "test.audit", self.account_a)
        other_event = record_audit(self.user_b, "test.audit", self.account_b)
        self.assertEqual(own_event.metadata["organization_id"], self.org_a.id)
        self.assertEqual(other_event.metadata["organization_id"], self.org_b.id)

        response = self.client.get("/api/audit-events/")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data}
        self.assertIn(own_event.id, ids)
        self.assertNotIn(other_event.id, ids)
        self.assertEqual(self.client.get(f"/api/audit-events/{other_event.id}/").status_code, 404)

    def test_node_parent_cannot_cross_workspace(self):
        response = self.client.post(
            "/api/organization-nodes/",
            {
                "organization": self.org_a.id,
                "parent": self.node_b.id,
                "name": "Invalid child",
                "node_type": "team",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_project_node_cannot_cross_workspace(self):
        response = self.client.post(
            "/api/projects/",
            {
                "organization": self.org_a.id,
                "node": self.node_b.id,
                "name": "Invalid project",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cloud_account_project_cannot_cross_workspace(self):
        response = self.client.post(
            "/api/cloud-accounts/",
            {
                "provider": "aws",
                "organization": self.org_a.id,
                "project": self.project_b.id,
                "name": "Invalid account",
                "provider_account_id": "999999999999",
                "role_arn": "arn:aws:iam::999999999999:role/FinopserReadOnly",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CloudAccount.objects.filter(provider_account_id="999999999999").exists())

    def test_audit_metadata_preserves_explicit_fields(self):
        event = record_audit(
            self.user_a,
            "test.explicit",
            self.account_a,
            {"organization_id": self.org_a.id, "detail": "kept"},
        )
        self.assertEqual(event.metadata["organization_id"], self.org_a.id)
        self.assertEqual(event.metadata["detail"], "kept")
        self.assertTrue(AuditEvent.objects.filter(pk=event.pk).exists())
