from .aws import AWSProvider
from .base import CloudProvider


def get_provider(name: str) -> CloudProvider:
    if name == "aws":
        return AWSProvider()
    raise ValueError(f"Unsupported cloud provider: {name}")
