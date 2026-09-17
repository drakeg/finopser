from django.test import SimpleTestCase

from .integration_models import ApiCredential, IntegrationDestination


class IntegrationDestinationCredentialSeparationTests(SimpleTestCase):
    def test_destination_and_api_credential_models_are_distinct(self):
        destination_fields = {field.name for field in IntegrationDestination._meta.get_fields()}
        credential_fields = {field.name for field in ApiCredential._meta.get_fields()}
        self.assertNotIn("token_digest", destination_fields)
        self.assertNotIn("endpoint_url", credential_fields)
