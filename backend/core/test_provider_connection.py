from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from .providers.base import CostResult, ProviderConnection
from .providers.registry import AWSFinOpsProvider


class ProviderConnectionTests(SimpleTestCase):
    def test_aws_validation_maps_neutral_auth_to_existing_role_inputs(self):
        provider = AWSFinOpsProvider()
        connection = ProviderConnection(provider_account_id="123456789012", auth={"role_arn":"arn:aws:iam::123456789012:role/Finopser","external_id":"tenant-1"})
        with patch.object(provider, "_assume_credentials", return_value={"AccessKeyId":"a","SecretAccessKey":"b","SessionToken":"c"}) as assume, patch("core.providers.aws.boto3.client") as client:
            client.return_value.get_caller_identity.return_value={"Account":"123456789012","Arn":"arn:aws:sts::123456789012:assumed-role/Finopser/session","UserId":"user"}
            result=provider.validate_connection(connection)
        self.assertEqual(result.provider_account_id,"123456789012")
        assume.assert_called_once_with(role_arn="arn:aws:iam::123456789012:role/Finopser",external_id="tenant-1",session_name="finopser-validation")

    @patch("core.providers.registry.fetch_aws_costs")
    def test_aws_costs_map_neutral_auth_to_existing_cost_adapter(self, fetch):
        fetch.return_value=CostResult(records=[])
        provider=AWSFinOpsProvider()
        connection=ProviderConnection(provider_account_id="123456789012",auth={"role_arn":"role","external_id":"external"})
        provider.fetch_costs(connection,start_date=date(2026,10,1),end_date=date(2026,10,2))
        fetch.assert_called_once_with(provider,account_id="123456789012",role_arn="role",external_id="external",start_date=date(2026,10,1),end_date=date(2026,10,2))
