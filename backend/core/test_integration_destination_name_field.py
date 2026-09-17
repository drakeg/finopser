from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationNameFieldTests(SimpleTestCase):
    def test_name_field_matches_api_limit(self):
        field = IntegrationDestination._meta.get_field("name")
        self.assertEqual(field.max_length, 120)
