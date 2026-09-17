from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationEndpointWhitespaceTests(SimpleTestCase):
    def test_outer_whitespace_is_removed(self):
        endpoint, error = _validated_endpoint("\nhttps://example.test/events\t")
        self.assertIsNone(error)
        self.assertEqual(endpoint, "https://example.test/events")
