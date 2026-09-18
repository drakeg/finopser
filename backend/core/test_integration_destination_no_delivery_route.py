from django.test import SimpleTestCase
from django.urls import resolve
from django.urls.exceptions import Resolver404


class IntegrationDestinationDeliveryRouteBoundaryTests(SimpleTestCase):
    def test_no_test_delivery_route_exists_yet(self):
        with self.assertRaises(Resolver404):
            resolve("/api/integrations/destinations/1/test/")
