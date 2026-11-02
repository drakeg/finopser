from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .account_api import connect_cloud_account
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
