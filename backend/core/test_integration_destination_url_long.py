from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationLongEndpointTests(SimpleTestCase):
    def test_endpoint_validator_rejects_over_500_chars(self):
        endpoint, error = _validated_endpoint("https://example.test/" + "x" * 500)
        self.assertIsNone(endpoint)
        self.assertIsNotNone(error)
