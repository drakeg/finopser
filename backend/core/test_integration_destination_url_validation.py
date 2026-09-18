from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationUrlValidationTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="URL Validation Tenant")
        owner = User.objects.create_user(username="url-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        self.client = APIClient()
        self.client.force_authenticate(owner)

    def test_rejects_non_http_endpoint(self):
        response = self.client.post(
            "/api/integrations/destinations/",
            {"name": "ftp", "endpoint_url": "ftp://example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_accepts_local_http_endpoint_for_future_fake_delivery_tests(self):
        response = self.client.post(
            "/api/integrations/destinations/",
            {"name": "local", "endpoint_url": "http://localhost:9999/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
