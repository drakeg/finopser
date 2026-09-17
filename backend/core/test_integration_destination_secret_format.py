from django.test import SimpleTestCase

from .integration_destination_api import _new_signing_material


class IntegrationDestinationSecretFormatTests(SimpleTestCase):
    def test_signing_secret_has_finopser_webhook_namespace(self):
        plaintext, _digest, _prefix = _new_signing_material()
        self.assertTrue(plaintext.startswith("finopser_whsec_"))
