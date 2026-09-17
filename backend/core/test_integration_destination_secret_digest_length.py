from django.test import SimpleTestCase

from .integration_destination_api import _new_signing_material


class IntegrationDestinationDigestLengthTests(SimpleTestCase):
    def test_digest_is_sha256_hex_length(self):
        _secret, digest, _prefix = _new_signing_material()
        self.assertEqual(len(digest), 64)
        int(digest, 16)
