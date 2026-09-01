from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from .account_models import Notification
from .costs import sync_costs
from .inventory import sync_inventory
from .models import CloudAccount, Organization, OrganizationNode, Project
from .providers import ProviderDiscoveryError
from .providers.base import ProviderCostError


class NotificationSyncSignalTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Sync Signal Org")
        node = OrganizationNode.objects.create(organization=self.organization, name="Root")
        project = Project.objects.create(
            organization=self.organization,
            node=node,
            name="Default",
        )
        self.account = CloudAccount.objects.create(
            organization=self.organization,
            project=project,
            name="AWS Production",
            provider_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/FinopserReadOnly",
            status=CloudAccount.Status.VALID,
        )

    @patch("core.inventory.get_provider")
    def test_failed_inventory_sync_coalesces(self, get_provider):
        provider = MagicMock()
        provider.discover_resources.side_effect = ProviderDiscoveryError("inventory unavailable")
        get_provider.return_value = provider

        sync_inventory(self.account)
        sync_inventory(self.account)

        notification = Notification.objects.get(
            organization=self.organization,
            dedupe_key=f"inventory-sync:{self.account.id}:failed",
        )
        self.assertEqual(notification.category, "operations")
        self.assertEqual(notification.severity, "critical")
        self.assertEqual(notification.target, "Accounts")
        self.assertEqual(notification.occurrence_count, 2)

    @patch("core.costs.get_provider")
    def test_partial_cost_sync_generates_actionable_notification(self, get_provider):
        provider = MagicMock()
        provider.fetch_costs.return_value = SimpleNamespace(
            records=[],
            errors=["Cost Explorer throttled"],
        )
        get_provider.return_value = provider

        sync_costs(
            self.account,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 9, 1),
        )

        notification = Notification.objects.get(
            organization=self.organization,
            dedupe_key=f"cost-sync:{self.account.id}:partial",
        )
        self.assertEqual(notification.severity, "high")
        self.assertEqual(notification.target, "Costs")
        self.assertEqual(notification.object_id, str(self.account.id))

    @patch("core.costs.get_provider")
    def test_failed_cost_sync_generates_critical_notification(self, get_provider):
        provider = MagicMock()
        provider.fetch_costs.side_effect = ProviderCostError("cost API unavailable")
        get_provider.return_value = provider

        sync_costs(
            self.account,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 9, 1),
        )

        notification = Notification.objects.get(
            organization=self.organization,
            dedupe_key=f"cost-sync:{self.account.id}:failed",
        )
        self.assertEqual(notification.severity, "critical")
        self.assertIn("cost API unavailable", notification.detail)

    @patch("core.inventory.get_provider")
    def test_successful_inventory_sync_stays_quiet(self, get_provider):
        provider = MagicMock()
        provider.discover_resources.return_value = SimpleNamespace(resources=[], errors=[])
        get_provider.return_value = provider

        sync_inventory(self.account)

        self.assertFalse(Notification.objects.filter(organization=self.organization).exists())
