from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationBlankEndpointTests(SimpleTestCase):
    def test_blank_endpoint_is_invalid(self):
        self.assertIsNotNone(_validated_endpoint("")[1])
        self.assertIsNotNone(_validated_endpoint("   ")[1])
        self.assertIsNotNone(_validated_endpoint(None)[1])
