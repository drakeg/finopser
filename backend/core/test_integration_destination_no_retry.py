from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationRetryBoundaryTests(SimpleTestCase):
    def test_slice_one_has_no_retry_state(self):
        field_names = {field.name for field in IntegrationDestination._meta.get_fields()}
        self.assertNotIn("retry_count", field_names)
        self.assertNotIn("next_retry_at", field_names)
        self.assertNotIn("last_delivery_at", field_names)
