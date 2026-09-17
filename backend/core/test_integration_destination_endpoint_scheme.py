from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationEndpointSchemeTests(SimpleTestCase):
    def test_endpoint_validator_allows_only_http_and_https(self):
        self.assertIsNone(_validated_endpoint("https://example.test/events")[1])
        self.assertIsNone(_validated_endpoint("http://localhost:9999/events")[1])
        self.assertIsNotNone(_validated_endpoint("ftp://example.test/events")[1])
        self.assertIsNotNone(_validated_endpoint("file:///tmp/events")[1])
