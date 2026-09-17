from django.test import SimpleTestCase

from .integration_models import IntegrationDestination


class IntegrationDestinationConstraintTests(SimpleTestCase):
    def test_model_declares_tenant_name_unique_constraint(self):
        names = {constraint.name for constraint in IntegrationDestination._meta.constraints}
        self.assertIn("uniq_integration_destination_org_name", names)
