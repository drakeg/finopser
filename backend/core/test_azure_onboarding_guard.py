from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .account_api import validate_cloud_account
from .models import CloudAccount, Organization
from .serializers import CloudAccountSerializer


class AzureOnboardingGuardTests(TestCase):
    def test_serializer_rejects_azure_with_current_message(self):
        serializer = CloudAccountSerializer(data={
            "provider": "azure", "name": "Test Azure",
            "provider_account_id": "123456789012",
            "role_arn": "arn:aws:iam::123456789012:role/Test",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("Azure onboarding is not configured", str(serializer.errors))

    @patch("core.account_api.get_provider")
    def test_azure_validation_does_not_invoke_provider(self, provider_factory):
        user = get_user_model().objects.create_user(username="azure-guard-test")
        organization = Organization.objects.create(name="Azure guard test")
        account = CloudAccount.objects.create(
            organization=organization, provider="azure", name="Azure",
            provider_account_id="11111111-1111-1111-1111-111111111111", role_arn="",
        )
        from .account_models import OnboardingProfile
        OnboardingProfile.objects.create(user=user, organization=organization)
        request = APIRequestFactory().post(f"/accounts/{account.pk}/validate/")
        force_authenticate(request, user=user)
        response = validate_cloud_account(request, account.pk)
        self.assertEqual(response.status_code, 400)
        self.assertIn("not configured", response.data["detail"])
        provider_factory.assert_not_called()
