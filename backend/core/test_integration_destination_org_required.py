from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


class IntegrationDestinationOrganizationTests(TestCase):
    def test_user_without_organization_cannot_manage_destinations(self):
        user = User.objects.create_user(username="no-org-destination", password="test-password-long")
        client = APIClient()
        client.force_authenticate(user)
        response = client.get("/api/integrations/destinations/")
        self.assertIn(response.status_code, {400, 403})
