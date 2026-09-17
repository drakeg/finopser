from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationHeaderBoundaryTests(SimpleTestCase):
    def test_model_does_not_store_arbitrary_headers(self):
        field_names = {field.name for field in IntegrationDestination._meta.get_fields()}
        self.assertNotIn("headers", field_names)
        self.assertNotIn("authorization", field_names)
        self.assertNotIn("authorization_header", field_names)
