from django.test import SimpleTestCase
from django.urls import reverse


class IntegrationDestinationRouteTests(SimpleTestCase):
    def test_destination_routes_are_named(self):
        self.assertEqual(reverse("integration-destinations"), "/api/integrations/destinations/")
        self.assertEqual(reverse("integration-destination-detail", args=[7]), "/api/integrations/destinations/7/")
        self.assertEqual(reverse("integration-destination-disable", args=[7]), "/api/integrations/destinations/7/disable/")
        self.assertEqual(reverse("integration-destination-enable", args=[7]), "/api/integrations/destinations/7/enable/")
