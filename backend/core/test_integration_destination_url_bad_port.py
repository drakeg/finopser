from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationMalformedPortTests(SimpleTestCase):
    def test_non_numeric_port_is_invalid(self):
        endpoint, error = _validated_endpoint("https://example.test:notaport/events")
        self.assertIsNone(endpoint)
        self.assertIsNotNone(error)
