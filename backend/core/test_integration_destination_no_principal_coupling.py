from django.test import SimpleTestCase

from .integration_models import IntegrationDestination, ServicePrincipal


class IntegrationDestinationPrincipalSeparationTests(SimpleTestCase):
    def test_destination_has_no_service_principal_identity_field(self):
        destination_fields = {field.name for field in IntegrationDestination._meta.get_fields()}
        principal_fields = {field.name for field in ServicePrincipal._meta.get_fields()}
        self.assertNotIn("service_principal", destination_fields)
        self.assertNotIn("endpoint_url", principal_fields)
