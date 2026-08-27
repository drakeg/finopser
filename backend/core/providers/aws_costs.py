from datetime import date
from decimal import Decimal

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from .base import CostRecord, CostResult, ProviderCostError


def fetch_aws_costs(provider, *, account_id: str, role_arn: str, start_date: date, end_date: date, external_id: str = "") -> CostResult:
    try:
        session = provider._assumed_session(
            role_arn=role_arn,
            external_id=external_id,
            session_name="finopser-costs",
        )
        client = session.client("ce", region_name="us-east-1", config=provider.config)
        records: list[CostRecord] = []
        next_token = None
        while True:
            request = {
                "TimePeriod": {"Start": start_date.isoformat(), "End": end_date.isoformat()},
                "Granularity": "DAILY",
                "Metrics": ["UnblendedCost"],
                "GroupBy": [
                    {"Type": "DIMENSION", "Key": "SERVICE"},
                    {"Type": "DIMENSION", "Key": "REGION"},
                ],
            }
            if next_token:
                request["NextPageToken"] = next_token
            response = client.get_cost_and_usage(**request)
            for period in response.get("ResultsByTime", []):
                usage_date = date.fromisoformat(period["TimePeriod"]["Start"])
                for group in period.get("Groups", []):
                    keys = list(group.get("Keys", []))
                    service = str(keys[0]) if keys else "Unknown"
                    region = str(keys[1]) if len(keys) > 1 else ""
                    metric = group.get("Metrics", {}).get("UnblendedCost", {})
                    records.append(
                        CostRecord(
                            usage_date=usage_date,
                            provider_account_id=account_id,
                            service=service,
                            region=region,
                            amount=Decimal(str(metric.get("Amount", "0"))),
                            currency=str(metric.get("Unit", "USD")),
                        )
                    )
            next_token = response.get("NextPageToken")
            if not next_token:
                break
    except (ClientError, BotoCoreError, NoCredentialsError, KeyError, ValueError) as exc:
        raise ProviderCostError(f"AWS cost sync failed: {provider._error_code(exc)}") from exc
    return CostResult(records=records)
