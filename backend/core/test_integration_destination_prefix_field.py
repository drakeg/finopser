from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationPrefixFieldTests(SimpleTestCase):
    def test_prefix_field_is_bounded(self):
        field = IntegrationDestination._meta.get_field("signing_secret_prefix")
        self.assertEqual(field.max_length, 16)
