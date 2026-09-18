from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationCreatorRelationTests(SimpleTestCase):
    def test_destination_creator_relation_is_explicit(self):
        field = IntegrationDestination._meta.get_field("created_by")
        self.assertEqual(field.remote_field.related_name, "created_integration_destinations")
