from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .account_api import connect_cloud_account, initial_sync, validate_cloud_account
from .account_models import OnboardingProfile
from .models import CloudAccount, Organization


class CloudAccountOnboardingSafetyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="onboarding-safety")
        self.organization = Organization.objects.create(name="Onboarding safety org")
        OnboardingProfile.objects.create(user=self.user, organization=self.organization)
        self.payload = {
            "name": "Production",
            "provider_account_id": "123456789012",
            "role_arn": "arn:aws:iam::123456789012:role/FinopserReadOnly",
        }

    def post(self, **changes):
        request = APIRequestFactory().post("/api/onboarding/cloud-account/", {**self.payload, **changes}, format="json")
        force_authenticate(request, user=self.user)
        return connect_cloud_account(request)

    def test_rejects_azure_without_creating_aws_record(self):
        response = self.post(provider="azure")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CloudAccount.objects.count(), 0)

    def test_rejects_long_lived_credentials(self):
        response = self.post(aws_secret_access_key="not-a-real-secret")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CloudAccount.objects.count(), 0)

    def test_rejects_mismatched_role_account(self):
        response = self.post(role_arn="arn:aws:iam::999999999999:role/FinopserReadOnly")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CloudAccount.objects.count(), 0)

    def test_rejects_malformed_role(self):
        response = self.post(role_arn="not-a-role")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CloudAccount.objects.count(), 0)

    def test_registers_azure_intent_without_credentials_or_validation(self):
        response = self.post(
            provider="azure",
            provider_account_id="11111111-1111-1111-1111-111111111111",
            tenant_id="22222222-2222-2222-2222-222222222222",
            role_arn=None,
        )
        # AWS role fields are forbidden, even when explicitly null.
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CloudAccount.objects.count(), 0)

        payload = {
            "provider": "azure",
            "name": "Azure test",
            "provider_account_id": "11111111-1111-1111-1111-111111111111",
            "tenant_id": "22222222-2222-2222-2222-222222222222",
        }
        request = APIRequestFactory().post("/api/onboarding/cloud-account/", payload, format="json")
        force_authenticate(request, user=self.user)
        response = connect_cloud_account(request)
        self.assertEqual(response.status_code, 201)
        account = CloudAccount.objects.get()
        self.assertEqual(account.provider, CloudAccount.Provider.AZURE)
        self.assertEqual(account.status, CloudAccount.Status.UNVALIDATED)
        self.assertEqual(account.role_arn, "")
        self.assertEqual(account.metadata["tenant_id"], payload["tenant_id"])

    def test_azure_rejects_credentials_and_bad_identifiers(self):
        for changes in (
            {"client_secret": "do-not-store"},
            {"provider_account_id": "not-a-uuid"},
            {"tenant_id": "not-a-uuid"},
        ):
            payload = {
                "provider": "azure",
                "name": "Azure test",
                "provider_account_id": "11111111-1111-1111-1111-111111111111",
                "tenant_id": "22222222-2222-2222-2222-222222222222",
                **changes,
            }
            request = APIRequestFactory().post("/api/onboarding/cloud-account/", payload, format="json")
            force_authenticate(request, user=self.user)
            self.assertEqual(connect_cloud_account(request).status_code, 400)
        self.assertEqual(CloudAccount.objects.count(), 0)

    def test_duplicate_azure_subscription_is_rejected(self):
        payload = {
            "provider": "azure",
            "name": "Azure test",
            "provider_account_id": "11111111-1111-1111-1111-111111111111",
            "tenant_id": "22222222-2222-2222-2222-222222222222",
        }
        for expected in (201, 400):
            request = APIRequestFactory().post("/api/onboarding/cloud-account/", payload, format="json")
            force_authenticate(request, user=self.user)
            self.assertEqual(connect_cloud_account(request).status_code, expected)
        self.assertEqual(CloudAccount.objects.count(), 1)

    @patch("core.account_api.sync_costs")
    @patch("core.account_api.sync_inventory")
    @patch("core.account_api.get_provider")
    def test_azure_sync_and_validation_fail_closed_even_if_marked_valid(self, provider, inventory, costs):
        account = CloudAccount.objects.create(
            organization=self.organization,
            provider=CloudAccount.Provider.AZURE,
            name="Azure test",
            provider_account_id="11111111-1111-1111-1111-111111111111",
            role_arn="",
            status=CloudAccount.Status.VALID,
            metadata={"tenant_id": "22222222-2222-2222-2222-222222222222"},
        )
        for endpoint in (validate_cloud_account, initial_sync):
            request = APIRequestFactory().post("/api/onboarding/azure/")
            force_authenticate(request, user=self.user)
            response = endpoint(request, account.pk)
            self.assertEqual(response.status_code, 400)
        provider.assert_not_called()
        inventory.assert_not_called()
        costs.assert_not_called()
