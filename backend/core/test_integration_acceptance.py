from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .integration_models import IntegrationDelivery, IntegrationDestination
from .models import AuditEvent, Organization


class IntegrationAcceptanceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Acceptance Tenant")
        self.manager = User.objects.create_user(username="acceptance-manager", password="test-password-long")
        OrganizationMembership.objects.create(
            user=self.manager,
            organization=self.organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)
        self.destination = IntegrationDestination.objects.create(
            organization=self.organization,
            name="acceptance-hook",
            endpoint_url="http://localhost:9999/hook",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="finopser_whsec_a",
            created_by=self.manager,
        )

    def test_local_test_records_sanitized_history_and_audit(self):
        response = self.client.post(f"/api/integrations/destinations/{self.destination.id}/test/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], IntegrationDelivery.Status.SUCCEEDED)
        self.assertNotIn("signing", response.data)
        history = self.client.get(f"/api/integrations/destinations/{self.destination.id}/deliveries/")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.data), 1)
        self.assertEqual(history.data[0]["id"], response.data["id"])
        self.assertTrue(AuditEvent.objects.filter(action="integration_destination.local_test").exists())

    def test_disabled_destination_rejects_local_test(self):
        self.destination.is_active = False
        self.destination.save(update_fields=["is_active"])
        response = self.client.post(f"/api/integrations/destinations/{self.destination.id}/test/", {}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertFalse(IntegrationDelivery.objects.exists())

    def test_cross_tenant_history_and_test_return_404(self):
        other = Organization.objects.create(name="Other Tenant")
        outsider = User.objects.create_user(username="other-manager", password="test-password-long")
        OrganizationMembership.objects.create(user=outsider, organization=other, role=OrganizationMembership.Role.OWNER)
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(f"/api/integrations/destinations/{self.destination.id}/deliveries/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/integrations/destinations/{self.destination.id}/test/", {}, format="json").status_code, 404)

    def test_non_manager_fails_closed(self):
        viewer = User.objects.create_user(username="acceptance-viewer", password="test-password-long")
        OrganizationMembership.objects.create(user=viewer, organization=self.organization, role=OrganizationMembership.Role.VIEWER)
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get(f"/api/integrations/destinations/{self.destination.id}/deliveries/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/integrations/destinations/{self.destination.id}/test/", {}, format="json").status_code, 403)
