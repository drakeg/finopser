from pathlib import Path

from django.test import SimpleTestCase


class IntegrationDestinationTaskBoundaryTests(SimpleTestCase):
    def test_destination_api_does_not_enqueue_background_delivery(self):
        source = Path(__file__).with_name("integration_destination_api.py").read_text()
        self.assertNotIn(".delay(", source)
        self.assertNotIn("apply_async", source)
