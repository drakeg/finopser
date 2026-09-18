from django.test import TestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationModelTests(TestCase):
    def test_webhook_is_the_only_supported_destination_type(self):
        self.assertEqual(
            list(IntegrationDestination.DestinationType.values),
            ["webhook"],
        )
