from django.test import SimpleTestCase

from .integration_destination_api import _new_signing_material


class IntegrationDestinationSecretStrengthTests(SimpleTestCase):
    def test_generated_secret_has_sufficient_length(self):
        secret, _digest, _prefix = _new_signing_material()
        self.assertGreaterEqual(len(secret), 40)
