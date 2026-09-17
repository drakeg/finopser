from django.test import SimpleTestCase

from .integration_destination_api import _new_signing_material


class IntegrationDestinationSecretUniquenessTests(SimpleTestCase):
    def test_generated_signing_material_is_unique(self):
        first = _new_signing_material()
        second = _new_signing_material()
        self.assertNotEqual(first[0], second[0])
        self.assertNotEqual(first[1], second[1])
