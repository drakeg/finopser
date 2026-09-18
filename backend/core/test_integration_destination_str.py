from django.contrib.auth.models import User
from django.test import TestCase

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationRepresentationTests(TestCase):
    def test_string_representation_contains_no_secret_material(self):
        organization = Organization.objects.create(name="Representation Tenant")
        owner = User.objects.create_user(username="repr-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        destination = IntegrationDestination.objects.create(
            organization=organization,
            name="events",
            endpoint_url="https://example.test/events",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="finopser_whsec_a",
            created_by=owner,
        )
        representation = str(destination)
        self.assertIn("events", representation)
        self.assertNotIn(destination.signing_secret_digest, representation)
        self.assertNotIn(destination.signing_secret_prefix, representation)
