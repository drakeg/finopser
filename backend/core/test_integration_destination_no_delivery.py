from django.test import SimpleTestCase

from . import integration_destination_api


class IntegrationDestinationSliceBoundaryTests(SimpleTestCase):
    def test_slice_one_has_no_delivery_entrypoint(self):
        self.assertFalse(hasattr(integration_destination_api, "deliver"))
        self.assertFalse(hasattr(integration_destination_api, "test_delivery"))
