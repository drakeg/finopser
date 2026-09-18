from django.test import TestCase
from rest_framework.test import APIClient


class IntegrationDestinationAuthenticationTests(TestCase):
    def test_anonymous_destination_listing_is_rejected(self):
        response = APIClient().get("/api/integrations/destinations/")
        self.assertIn(response.status_code, {401, 403})
