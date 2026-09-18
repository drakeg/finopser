from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationDefaultOrderingTests(SimpleTestCase):
    def test_model_ordering_is_stable(self):
        self.assertEqual(IntegrationDestination._meta.ordering, ["name", "id"])
