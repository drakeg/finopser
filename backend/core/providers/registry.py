from .aws import AWSProvider
from .aws_costs import fetch_aws_costs
from .base import CloudProvider


class AWSFinOpsProvider(AWSProvider):
    def fetch_costs(self, **kwargs):
        return fetch_aws_costs(self, **kwargs)


def get_provider(name: str) -> CloudProvider:
    if name == "aws":
        return AWSFinOpsProvider()
    raise ValueError(f"Unsupported cloud provider: {name}")
