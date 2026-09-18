from django.test import SimpleTestCase
from django.urls import resolve
from django.urls.exceptions import Resolver404


class IntegrationDestinationRotationBoundaryTests(SimpleTestCase):
    def test_slice_one_has_no_destination_secret_rotation_route(self):
        with self.assertRaises(Resolver404):
            resolve("/api/integrations/destinations/1/rotate/")
