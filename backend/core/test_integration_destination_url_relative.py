from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationRelativeUrlTests(SimpleTestCase):
    def test_relative_endpoint_is_invalid(self):
        endpoint, error = _validated_endpoint("/events")
        self.assertIsNone(endpoint)
        self.assertIsNotNone(error)
