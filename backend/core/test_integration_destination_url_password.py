from django.test import SimpleTestCase

from .integration_destination_api import _validated_endpoint


class IntegrationDestinationEndpointUserinfoTests(SimpleTestCase):
    def test_endpoint_validator_rejects_userinfo(self):
        endpoint, error = _validated_endpoint("https://user:password@example.test/events")
        self.assertIsNone(endpoint)
        self.assertIsNotNone(error)
