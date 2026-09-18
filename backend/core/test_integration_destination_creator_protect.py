from django.contrib.auth.models import User
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from .account_models import OrganizationMembership
from .integration_models import IntegrationDestination
from .models import Organization


class IntegrationDestinationCreatorProtectionTests(TestCase):
    def test_creator_cannot_be_deleted_while_destination_exists(self):
        organization = Organization.objects.create(name="Creator Protection Tenant")
        owner = User.objects.create_user(username="protected-owner", password="test-password-long")
        OrganizationMembership.objects.create(
            user=owner,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        IntegrationDestination.objects.create(
            organization=organization,
            name="events",
            endpoint_url="https://example.test/events",
            signing_secret_digest="a" * 64,
            signing_secret_prefix="prefix",
            created_by=owner,
        )
        with self.assertRaises(ProtectedError):
            owner.delete()
