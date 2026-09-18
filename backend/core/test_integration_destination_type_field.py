from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationTypeFieldTests(SimpleTestCase):
    def test_destination_type_field_has_webhook_choice(self):
        field = IntegrationDestination._meta.get_field("destination_type")
        self.assertEqual(field.max_length, 32)
        self.assertEqual(dict(field.choices), {"webhook": "Webhook"})
