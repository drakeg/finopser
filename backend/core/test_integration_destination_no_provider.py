from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationProviderBoundaryTests(SimpleTestCase):
    def test_only_generic_webhook_provider_is_enabled(self):
        values = set(IntegrationDestination.DestinationType.values)
        self.assertEqual(values, {"webhook"})
        self.assertNotIn("slack", values)
        self.assertNotIn("teams", values)
        self.assertNotIn("pagerduty", values)
