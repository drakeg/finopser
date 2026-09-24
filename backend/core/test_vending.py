from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import AuditEvent, Organization
from .vending_execution import ProvisioningResult
from .vending_models import (
    AccountProvisioningExecution,
    AccountProvisioningPlan,
    AccountVendingRequest,
)


class AccountVendingTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Vending Workspace")
        self.owner = User.objects.create_user(username="vending-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.member = User.objects.create_user(username="vending-member", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.member,
            organization=self.organization,
            role=OrganizationMembership.Role.MEMBER,
        )
        self.other_organization = Organization.objects.create(name="Other Vending Workspace")
        self.other_owner = User.objects.create_user(username="other-vending-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.other_owner,
            organization=self.other_organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client = APIClient()

    def _create(self, user=None, email="new-account@example.com"):
        self.client.force_authenticate(user or self.member)
        return self.client.post(
            "/api/account-vending/requests/",
            {
                "account_name": "New workload",
                "account_email": email,
                "environment": "production",
                "purpose": "Customer workload",
                "baseline_profile": "production",
            },
            format="json",
        )

    def test_member_can_request_but_cannot_approve(self):
        created = self._create()
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "pending_approval")

        denied = self.client.post(
            f"/api/account-vending/requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_manager_approval_enables_preview_readiness_without_live_provisioning(self):
        created = self._create()
        self.client.force_authenticate(self.owner)
        approved = self.client.post(
            f"/api/account-vending/requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], "approved")

        preview = self.client.get(f"/api/account-vending/requests/{created.data['id']}/preview/")
        self.assertEqual(preview.status_code, 200)
        self.assertTrue(preview.data["ready_for_provisioning"])
        self.assertFalse(preview.data["live_provisioning"])
        self.assertEqual(preview.data["provider"], "disabled")
        self.assertIn("production-guardrails", preview.data["intended_actions"])
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="account_vending.preview",
            ).exists()
        )

    def test_manager_can_reject_pending_request_with_reason(self):
        created = self._create()
        self.client.force_authenticate(self.owner)
        rejected = self.client.post(
            f"/api/account-vending/requests/{created.data['id']}/reject/",
            {"reason": "Use the shared sandbox account."},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.data["status"], "rejected")
        self.assertEqual(rejected.data["rejection_reason"], "Use the shared sandbox account.")

    def test_requests_are_tenant_scoped(self):
        own = self._create(user=self.owner)
        other = self._create(user=self.other_owner, email="other@example.com")
        self.assertEqual(own.status_code, 201)
        self.assertEqual(other.status_code, 201)

        self.client.force_authenticate(self.owner)
        listing = self.client.get("/api/account-vending/requests/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([item["id"] for item in listing.data], [own.data["id"]])

        hidden = self.client.get(f"/api/account-vending/requests/{other.data['id']}/preview/")
        self.assertEqual(hidden.status_code, 404)

    def test_duplicate_email_is_rejected_within_workspace_only(self):
        first = self._create(user=self.owner, email="same@example.com")
        duplicate = self._create(user=self.owner, email="SAME@example.com")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(AccountVendingRequest.objects.filter(organization=self.organization).count(), 1)

    def test_cross_tenant_placement_is_rejected(self):
        from .models import OrganizationNode

        other_node = OrganizationNode.objects.create(
            organization=self.other_organization,
            name="Other node",
        )
        self.client.force_authenticate(self.member)
        response = self.client.post(
            "/api/account-vending/requests/",
            {
                "account_name": "Bad placement",
                "account_email": "bad-placement@example.com",
                "environment": "test",
                "organization_node": other_node.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AccountVendingRequest.objects.filter(organization=self.organization).exists())


    def test_approved_request_creates_idempotent_disabled_provisioning_plan(self):
        created = self._create()
        self.client.force_authenticate(self.owner)
        self.client.post(
            f"/api/account-vending/requests/{created.data['id']}/approve/",
            {},
            format="json",
        )

        url = f"/api/account-vending/requests/{created.data['id']}/plan/"
        first = self.client.post(url, {}, format="json")
        second = self.client.post(url, {}, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(AccountProvisioningPlan.objects.count(), 1)
        self.assertEqual(first.data["provider"], "disabled")
        self.assertFalse(first.data["live_provisioning"])
        self.assertEqual(first.data["intent"]["request_id"], created.data["id"])
        self.assertEqual(first.data["intent"]["baseline"]["profile"], "production")
        self.assertIn("production-guardrails", first.data["intent"]["baseline"]["actions"])
        self.assertEqual(AccountVendingRequest.objects.get(pk=created.data["id"]).status, "approved")
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="account_vending.plan",
            ).exists()
        )

    def test_plan_creation_requires_manager_approved_request_and_tenant_scope(self):
        pending = self._create()
        url = f"/api/account-vending/requests/{pending.data['id']}/plan/"

        denied = self.client.post(url, {}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(AccountProvisioningPlan.objects.exists())

        self.client.force_authenticate(self.owner)
        not_approved = self.client.post(url, {}, format="json")
        self.assertEqual(not_approved.status_code, 409)
        self.assertFalse(AccountProvisioningPlan.objects.exists())

        other = self._create(user=self.other_owner, email="plan-other@example.com")
        self.client.force_authenticate(self.other_owner)
        self.client.post(
            f"/api/account-vending/requests/{other.data['id']}/approve/",
            {},
            format="json",
        )
        self.client.force_authenticate(self.owner)
        hidden = self.client.post(
            f"/api/account-vending/requests/{other.data['id']}/plan/",
            {},
            format="json",
        )
        self.assertEqual(hidden.status_code, 404)
        self.assertFalse(AccountProvisioningPlan.objects.exists())

    def test_workspace_member_can_read_existing_plan_but_not_create_one(self):
        created = self._create()
        self.client.force_authenticate(self.owner)
        self.client.post(
            f"/api/account-vending/requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        url = f"/api/account-vending/requests/{created.data['id']}/plan/"
        planned = self.client.post(url, {}, format="json")
        self.assertEqual(planned.status_code, 201)

        self.client.force_authenticate(self.member)
        read = self.client.get(url)
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.data["id"], planned.data["id"])
        self.assertFalse(read.data["live_provisioning"])


    def _approved_plan(self):
        created = self._create()
        self.client.force_authenticate(self.owner)
        self.client.post(
            f"/api/account-vending/requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        self.client.post(
            f"/api/account-vending/requests/{created.data['id']}/plan/",
            {},
            format="json",
        )
        return created

    def test_default_execution_adapter_fails_closed_without_provider_mutation(self):
        created = self._approved_plan()
        url = f"/api/account-vending/requests/{created.data['id']}/executions/"
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "failed")
        self.assertEqual(response.data["provider"], "disabled")
        self.assertEqual(response.data["result"], {"outcome": "provider_disabled"})
        self.assertEqual(AccountVendingRequest.objects.get(pk=created.data["id"]).status, "approved")
        self.assertFalse(AccountProvisioningPlan.objects.get().live_provisioning)

    def test_fake_adapter_success_records_only_sanitized_result_metadata(self):
        created = self._approved_plan()
        url = f"/api/account-vending/requests/{created.data['id']}/executions/"

        class FakeAdapter:
            provider = "fake"

            def execute(self, intent):
                self.intent = intent
                return ProvisioningResult(
                    provider="fake",
                    reference="fake-account-123",
                    message="Local fake provisioning completed.",
                )

        adapter = FakeAdapter()
        with patch("core.vending_api.PROVISIONING_ADAPTER", adapter):
            response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "succeeded")
        self.assertEqual(response.data["provider"], "fake")
        self.assertEqual(
            response.data["result"],
            {
                "outcome": "succeeded",
                "reference": "fake-account-123",
                "message": "Local fake provisioning completed.",
            },
        )
        self.assertEqual(adapter.intent, AccountProvisioningPlan.objects.get().intent)
        self.assertNotIn("credentials", response.data["result"])
        self.assertNotIn("secret", response.data["result"])
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="account_vending.execute_completed",
            ).exists()
        )

    def test_execution_is_manager_only_tenant_scoped_and_rejects_active_attempt(self):
        created = self._approved_plan()
        url = f"/api/account-vending/requests/{created.data['id']}/executions/"
        self.client.force_authenticate(self.member)
        denied = self.client.post(url, {}, format="json")
        self.assertEqual(denied.status_code, 403)

        plan = AccountProvisioningPlan.objects.get()
        AccountProvisioningExecution.objects.create(
            plan=plan,
            organization=self.organization,
            requested_by=self.owner,
            status=AccountProvisioningExecution.Status.RUNNING,
        )
        self.client.force_authenticate(self.owner)
        conflict = self.client.post(url, {}, format="json")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(AccountProvisioningExecution.objects.count(), 1)

        other = self._create(user=self.other_owner, email="execute-other@example.com")
        self.client.force_authenticate(self.owner)
        hidden = self.client.get(
            f"/api/account-vending/requests/{other.data['id']}/executions/"
        )
        self.assertEqual(hidden.status_code, 404)
