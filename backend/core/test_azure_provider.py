from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from .providers.azure import AzureProvider
from .providers.base import ProviderConnection, ProviderCostError, ProviderValidationError


class FakeAzureAdapter:
    def subscription(self, subscription_id, auth): return {"subscription_id":subscription_id,"resource_id":f"/subscriptions/{subscription_id}","display_name":"Dev"}
    def resources(self, subscription_id, auth): return [{"id":f"/subscriptions/{subscription_id}/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1","type":"Microsoft.Compute/virtualMachines","name":"vm1","location":"eastus","tags":{"env":"dev"}}]
    def costs(self, subscription_id, auth, start_date, end_date): return [{"usage_date":start_date,"service":"Virtual Machines","region":"eastus","amount":"12.34","currency":"USD"}]


class AzureProviderTests(SimpleTestCase):
    def setUp(self):
        self.connection=ProviderConnection(provider_account_id="sub-123",auth={"tenant_id":"tenant","client_id":"client"})
        self.provider=AzureProvider(FakeAzureAdapter())

    def test_validates_subscription_identity(self):
        result=self.provider.validate_connection(self.connection)
        self.assertEqual(result.provider_account_id,"sub-123")
        self.assertEqual(result.metadata["display_name"],"Dev")

    def test_rejects_subscription_identity_mismatch(self):
        class Wrong(FakeAzureAdapter):
            def subscription(self, subscription_id, auth): return {"subscription_id":"other"}
        with self.assertRaisesMessage(ProviderValidationError,"subscription identity mismatch"):
            AzureProvider(Wrong()).validate_connection(self.connection)

    def test_normalizes_resources(self):
        resource=self.provider.discover_resources(self.connection).resources[0]
        self.assertEqual(resource.resource_type,"microsoft.compute/virtualmachines")
        self.assertEqual(resource.region,"eastus")
        self.assertEqual(resource.tags,{"env":"dev"})

    def test_normalizes_costs(self):
        record=self.provider.fetch_costs(self.connection,start_date=date(2026,10,1),end_date=date(2026,10,2)).records[0]
        self.assertEqual(record.amount,Decimal("12.34"))
        self.assertEqual(record.provider_account_id,"sub-123")

    def test_adapter_failures_are_safe(self):
        class Broken(FakeAzureAdapter):
            def costs(self,*args): raise RuntimeError("secret provider detail")
        with self.assertRaisesMessage(ProviderCostError,"Azure cost retrieval failed: RuntimeError"):
            AzureProvider(Broken()).fetch_costs(self.connection,start_date=date(2026,10,1),end_date=date(2026,10,2))
