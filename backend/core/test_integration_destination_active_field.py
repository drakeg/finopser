from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationActiveFieldTests(SimpleTestCase):
    def test_active_field_defaults_true(self):
        field = IntegrationDestination._meta.get_field("is_active")
        self.assertTrue(field.default)
