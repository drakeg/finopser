from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationSchemaTests(SimpleTestCase):
    def test_model_has_no_plaintext_secret_field(self):
        field_names = {field.name for field in IntegrationDestination._meta.get_fields()}
        self.assertNotIn("signing_secret", field_names)
        self.assertIn("signing_secret_digest", field_names)
        self.assertIn("signing_secret_prefix", field_names)
