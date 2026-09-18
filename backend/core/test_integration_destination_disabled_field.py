from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationDisabledFieldTests(SimpleTestCase):
    def test_disabled_timestamp_is_nullable(self):
        field = IntegrationDestination._meta.get_field("disabled_at")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
