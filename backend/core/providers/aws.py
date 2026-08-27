import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from .base import ProviderValidationError, ValidationResult


class AWSProvider:
    name = "aws"

    def __init__(self):
        self.config = Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 2, "mode": "standard"},
        )

    def validate_account(self, *, account_id: str, role_arn: str, external_id: str = "") -> ValidationResult:
        assume_args = {
            "RoleArn": role_arn,
            "RoleSessionName": "finopser-validation",
            "DurationSeconds": 900,
        }
        if external_id:
            assume_args["ExternalId"] = external_id

        try:
            source_sts = boto3.client("sts", config=self.config)
            assumed = source_sts.assume_role(**assume_args)
            credentials = assumed["Credentials"]
            assumed_sts = boto3.client(
                "sts",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                config=self.config,
            )
            identity = assumed_sts.get_caller_identity()
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "ClientError")
            raise ProviderValidationError(f"AWS validation failed: {code}") from exc
        except (BotoCoreError, NoCredentialsError, KeyError) as exc:
            raise ProviderValidationError(f"AWS validation failed: {exc.__class__.__name__}") from exc

        actual_account_id = str(identity.get("Account", ""))
        if actual_account_id != account_id:
            raise ProviderValidationError("AWS validation failed: account identity mismatch")

        return ValidationResult(
            provider_account_id=actual_account_id,
            arn=str(identity.get("Arn", "")),
            metadata={"user_id": str(identity.get("UserId", ""))},
        )
