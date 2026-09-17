from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationOrganizationRelationTests(SimpleTestCase):
    def test_destination_has_tenant_relation(self):
        field = IntegrationDestination._meta.get_field("organization")
        self.assertEqual(field.remote_field.related_name, "integration_destinations")
