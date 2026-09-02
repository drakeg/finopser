from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .audit import record_audit
from .models import AuditEvent, Organization


class AuditIntegrityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="audit-owner", password="test-password-long")
        self.organization = Organization.objects.create(name="Audit Integrity Workspace")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.other_organization = Organization.objects.create(name="Other Audit Workspace")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_checkpoint_verifies_tenant_history_and_ignores_other_tenant(self):
        own = record_audit(self.user, "organization.update", self.organization, {"field": "name"})
        AuditEvent.objects.create(
            organization=self.other_organization,
            action="other.secret",
            object_type="Organization",
            object_id=str(self.other_organization.id),
            object_repr=self.other_organization.name,
            metadata={"secret": "other-tenant"},
        )

        response = self.client.post("/api/audit-integrity/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "valid")
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["event_count"], 1)
        self.assertEqual(response.data["through_event_id"], own.id)
        self.assertEqual(response.data["unchecked_event_count"], 0)

    def test_events_after_checkpoint_are_reported_as_unchecked(self):
        record_audit(self.user, "organization.update", self.organization)
        created = self.client.post("/api/audit-integrity/", {}, format="json")
        self.assertEqual(created.status_code, 201)

        record_audit(self.user, "organization.read", self.organization)
        verified = self.client.get("/api/audit-integrity/")

        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.data["status"], "valid")
        self.assertEqual(verified.data["unchecked_event_count"], 1)

    def test_tampering_before_checkpoint_is_detected(self):
        event = record_audit(self.user, "organization.update", self.organization, {"field": "name"})
        created = self.client.post("/api/audit-integrity/", {}, format="json")
        self.assertEqual(created.status_code, 201)

        AuditEvent.objects.filter(pk=event.pk).update(metadata={"field": "tampered"})
        verified = self.client.get("/api/audit-integrity/")

        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.data["status"], "invalid")
        self.assertFalse(verified.data["valid"])

    def test_other_tenant_tampering_does_not_invalidate_checkpoint(self):
        record_audit(self.user, "organization.update", self.organization)
        other = AuditEvent.objects.create(
            organization=self.other_organization,
            action="other.update",
            object_type="Organization",
            object_id=str(self.other_organization.id),
            object_repr=self.other_organization.name,
            metadata={"value": "original"},
        )
        created = self.client.post("/api/audit-integrity/", {}, format="json")
        self.assertEqual(created.status_code, 201)

        AuditEvent.objects.filter(pk=other.pk).update(metadata={"value": "tampered"})
        verified = self.client.get("/api/audit-integrity/")

        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.data["status"], "valid")
        self.assertTrue(verified.data["valid"])
