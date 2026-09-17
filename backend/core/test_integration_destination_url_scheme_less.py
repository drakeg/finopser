from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationSchemeLessUrlTests(SimpleTestCase):
    def test_scheme_less_endpoint_is_invalid(self):
        endpoint, error = _validated_endpoint("example.test/events")
        self.assertIsNone(endpoint)
        self.assertIsNotNone(error)
