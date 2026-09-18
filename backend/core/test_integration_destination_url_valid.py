from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationValidEndpointTests(SimpleTestCase):
    def test_endpoint_validator_returns_trimmed_url(self):
        endpoint, error = _validated_endpoint("  https://example.test/events  ")
        self.assertIsNone(error)
        self.assertEqual(endpoint, "https://example.test/events")
