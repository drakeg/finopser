from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .account_models import OrganizationMembership
from .audit import record_audit
from .compliance import evaluate_compliance
from .models import AuditEvent, Organization
from .policies import evaluate_policies


class HistoryOwnershipTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="history-a", password="password")
        self.user_b = User.objects.create_user(username="history-b", password="password")
        self.org_a = Organization.objects.create(name="History A")
        self.org_b = Organization.objects.create(name="History B")
        OrganizationMembership.objects.create(
            user=self.user_a,
            organization=self.org_a,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            user=self.user_b,
            organization=self.org_b,
            role=OrganizationMembership.Role.OWNER,
        )

    def test_new_evaluation_runs_store_explicit_organization(self):
        compliance_a = evaluate_compliance(self.user_a)
        compliance_b = evaluate_compliance(self.user_b)
        policy_a = evaluate_policies(self.user_a)
        policy_b = evaluate_policies(self.user_b)

        self.assertEqual(compliance_a.organization_id, self.org_a.id)
        self.assertEqual(compliance_b.organization_id, self.org_b.id)
        self.assertEqual(policy_a.organization_id, self.org_a.id)
        self.assertEqual(policy_b.organization_id, self.org_b.id)

    def test_audit_events_store_explicit_organization(self):
        event_a = record_audit(self.user_a, "history.test", self.org_a)
        event_b = record_audit(self.user_b, "history.test", self.org_b)

        self.assertEqual(event_a.organization_id, self.org_a.id)
        self.assertEqual(event_b.organization_id, self.org_b.id)
        self.assertEqual(
            AuditEvent.objects.filter(organization=self.org_a, action="history.test").count(),
            1,
        )
        self.assertEqual(
            AuditEvent.objects.filter(organization=self.org_b, action="history.test").count(),
            1,
        )
