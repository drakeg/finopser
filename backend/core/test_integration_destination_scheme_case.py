from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .account_models import OrganizationMembership
from .models import Organization


class IntegrationDestinationSchemeCaseTests(TestCase):
    def test_uppercase_http_scheme_is_accepted_by_url_parser(self):
        organization = Organization.objects.create(name="Scheme Case Tenant")
        owner = User.objects.create_user(username="scheme-case-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/integrations/destinations/",
            {"name": "events", "endpoint_url": "HTTPS://example.test/events"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
