from unittest.mock import Mock, patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import AuditEvent, CloudAccount, CloudResource, Organization
from .providers import DiscoveryResult, ResourceRecord
from .rbac import PLATFORM_ADMIN


class InventoryApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="inventory-admin", password="password")
        Group.objects.get_or_create(name=PLATFORM_ADMIN)[0].user_set.add(self.admin)
        self.client.force_authenticate(self.admin)
        self.organization = Organization.objects.create(name="Inventory Org")
        self.account = CloudAccount.objects.create(
            provider=CloudAccount.Provider.AWS,
            organization=self.organization,
            name="Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
            last_validated_at=timezone.now(),
        )

    @staticmethod
    def records():
        return [
            ResourceRecord(
                provider_resource_id="ec2:123456789012:us-east-1:i-123",
                resource_type="aws.ec2.instance",
                name="web-1",
                region="us-east-1",
                state="running",
                tags={"Name": "web-1"},
            ),
            ResourceRecord(
                provider_resource_id="arn:aws:s3:::example-bucket",
                resource_type="aws.s3.bucket",
                name="example-bucket",
                region="global",
                state="available",
            ),
        ]

    @patch("core.inventory.get_provider")
    def test_validated_account_can_sync_inventory_idempotently(self, get_provider):
        provider = Mock()
        provider.discover_resources.return_value = DiscoveryResult(resources=self.records())
        get_provider.return_value = provider

        response = self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["created_count"], 2)
        self.assertEqual(CloudResource.objects.count(), 2)
        first_seen = CloudResource.objects.get(name="web-1").first_seen

        response = self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["created_count"], 0)
        self.assertEqual(response.data["updated_count"], 2)
        self.assertEqual(CloudResource.objects.get(name="web-1").first_seen, first_seen)
        self.assertTrue(
            AuditEvent.objects.filter(action="inventory_sync_success").exists()
        )

    @patch("core.inventory.get_provider")
    def test_successful_sync_marks_missing_resources_inactive(self, get_provider):
        provider = Mock()
        provider.discover_resources.side_effect = [
            DiscoveryResult(resources=self.records()),
            DiscoveryResult(resources=self.records()[:1]),
        ]
        get_provider.return_value = provider

        self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")
        response = self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")
        self.assertEqual(response.data["stale_count"], 1)
        bucket = CloudResource.objects.get(resource_type="aws.s3.bucket")
        self.assertFalse(bucket.is_active)

    @patch("core.inventory.get_provider")
    def test_partial_sync_does_not_mark_missing_resources_stale(self, get_provider):
        provider = Mock()
        provider.discover_resources.side_effect = [
            DiscoveryResult(resources=self.records()),
            DiscoveryResult(
                resources=self.records()[:1],
                errors=["s3:global:AccessDenied"],
            ),
        ]
        get_provider.return_value = provider

        self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")
        response = self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "partial")
        self.assertEqual(response.data["stale_count"], 0)
        self.assertTrue(CloudResource.objects.get(resource_type="aws.s3.bucket").is_active)

    @patch("core.inventory.get_provider")
    def test_resource_api_filters_inventory(self, get_provider):
        provider = Mock()
        provider.discover_resources.return_value = DiscoveryResult(resources=self.records())
        get_provider.return_value = provider
        self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")

        response = self.client.get("/api/resources/?resource_type=aws.ec2.instance&region=us-east-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "web-1")

    def test_unvalidated_account_cannot_sync(self):
        self.account.status = CloudAccount.Status.UNVALIDATED
        self.account.save(update_fields=["status"])
        response = self.client.post(f"/api/cloud-accounts/{self.account.id}/sync-inventory/")
        self.assertEqual(response.status_code, 400)
