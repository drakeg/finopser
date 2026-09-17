from django.contrib.auth.models import User
from django.test import TestCase

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationOrganizationCascadeTests(TestCase):
    def test_destination_is_removed_with_organization(self):
        organization = Organization.objects.create(name="Cascade Tenant")
        owner = User.objects.create_user(username="cascade-owner", password="test-password-long")
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
            signing_secret_prefix="prefix",
            created_by=owner,
        )
        destination_id = destination.id
        organization.delete()
        self.assertFalse(IntegrationDestination.objects.filter(pk=destination_id).exists())
