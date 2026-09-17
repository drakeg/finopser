from django.test import SimpleTestCase

from .integration_destination_api import _new_signing_material


class IntegrationDestinationSecretPrefixLengthTests(SimpleTestCase):
    def test_secret_prefix_fits_model_field(self):
        _secret, _digest, prefix = _new_signing_material()
        self.assertLessEqual(len(prefix), 16)
