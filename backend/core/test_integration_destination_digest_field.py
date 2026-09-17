from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationDigestFieldTests(SimpleTestCase):
    def test_digest_field_matches_sha256_hex(self):
        field = IntegrationDestination._meta.get_field("signing_secret_digest")
        self.assertEqual(field.max_length, 64)
