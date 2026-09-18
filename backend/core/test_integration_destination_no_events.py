from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationEventBoundaryTests(SimpleTestCase):
    def test_slice_one_has_no_event_subscription_field(self):
        field_names = {field.name for field in IntegrationDestination._meta.get_fields()}
        self.assertNotIn("events", field_names)
        self.assertNotIn("event_types", field_names)
        self.assertNotIn("subscriptions", field_names)
