from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationSecretNoticeTests(TestCase):
    def test_creation_warns_that_signing_secret_is_copy_once(self):
        organization = Organization.objects.create(name="Secret Notice Tenant")
        owner = User.objects.create_user(username="notice-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "https://example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("Copy", response.data["secret_notice"])
        self.assertIn("does not display it again", response.data["secret_notice"])
