from django.test import SimpleTestCase

from .integration_destination_api import _new_signing_material


class IntegrationDestinationSecretPrefixTests(SimpleTestCase):
    def test_prefix_does_not_reveal_full_secret(self):
        plaintext, digest, prefix = _new_signing_material()
        self.assertTrue(plaintext.startswith(prefix))
        self.assertNotEqual(prefix, plaintext)
        self.assertEqual(len(digest), 64)
        self.assertNotIn(plaintext, digest)
