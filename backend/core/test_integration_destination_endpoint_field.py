from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationEndpointFieldTests(SimpleTestCase):
    def test_endpoint_field_supports_bounded_urls(self):
        field = IntegrationDestination._meta.get_field("endpoint_url")
        self.assertEqual(field.max_length, 500)
