import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from .base import (
    DiscoveryResult,
    ProviderDiscoveryError,
    ProviderValidationError,
    ResourceRecord,
    ValidationResult,
)


class AWSProvider:
    name = "aws"

    def __init__(self):
        self.config = Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 2, "mode": "standard"},
        )

    def _assume_credentials(self, *, role_arn: str, external_id: str, session_name: str):
        assume_args = {
            "RoleArn": role_arn,
            "RoleSessionName": session_name,
            "DurationSeconds": 900,
        }
        if external_id:
            assume_args["ExternalId"] = external_id
        source_sts = boto3.client("sts", config=self.config)
        return source_sts.assume_role(**assume_args)["Credentials"]

    def _assumed_session(self, *, role_arn: str, external_id: str, session_name: str):
        credentials = self._assume_credentials(
            role_arn=role_arn,
            external_id=external_id,
            session_name=session_name,
        )
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    @staticmethod
    def _error_code(exc: Exception) -> str:
        if isinstance(exc, ClientError):
            return str(exc.response.get("Error", {}).get("Code", "ClientError"))
        return exc.__class__.__name__

    def validate_account(self, *, account_id: str, role_arn: str, external_id: str = "") -> ValidationResult:
        try:
            credentials = self._assume_credentials(
                role_arn=role_arn,
                external_id=external_id,
                session_name="finopser-validation",
            )
            assumed_sts = boto3.client(
                "sts",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                config=self.config,
            )
            identity = assumed_sts.get_caller_identity()
        except ClientError as exc:
            raise ProviderValidationError(
                f"AWS validation failed: {self._error_code(exc)}"
            ) from exc
        except (BotoCoreError, NoCredentialsError, KeyError) as exc:
            raise ProviderValidationError(
                f"AWS validation failed: {exc.__class__.__name__}"
            ) from exc

        actual_account_id = str(identity.get("Account", ""))
        if actual_account_id != account_id:
            raise ProviderValidationError("AWS validation failed: account identity mismatch")

        return ValidationResult(
            provider_account_id=actual_account_id,
            arn=str(identity.get("Arn", "")),
            metadata={"user_id": str(identity.get("UserId", ""))},
        )

    def discover_resources(
        self,
        *,
        account_id: str,
        role_arn: str,
        external_id: str = "",
    ) -> DiscoveryResult:
        try:
            session = self._assumed_session(
                role_arn=role_arn,
                external_id=external_id,
                session_name="finopser-inventory",
            )
        except (ClientError, BotoCoreError, NoCredentialsError, KeyError) as exc:
            raise ProviderDiscoveryError(
                f"AWS inventory failed: {self._error_code(exc)}"
            ) from exc

        resources: list[ResourceRecord] = []
        errors: list[str] = []
        regions: list[str] = []

        try:
            ec2 = session.client("ec2", region_name="us-east-1", config=self.config)
            response = ec2.describe_regions(AllRegions=False)
            regions = sorted(
                region["RegionName"]
                for region in response.get("Regions", [])
                if region.get("RegionName")
            )
        except (ClientError, BotoCoreError) as exc:
            errors.append(f"ec2:regions:{self._error_code(exc)}")

        try:
            s3 = session.client("s3", region_name="us-east-1", config=self.config)
            for bucket in s3.list_buckets().get("Buckets", []):
                name = str(bucket.get("Name", ""))
                if not name:
                    continue
                created = bucket.get("CreationDate")
                resources.append(
                    ResourceRecord(
                        provider_resource_id=f"arn:aws:s3:::{name}",
                        resource_type="aws.s3.bucket",
                        name=name,
                        region="global",
                        state="available",
                        metadata={
                            "creation_date": created.isoformat() if created else "",
                        },
                    )
                )
        except (ClientError, BotoCoreError) as exc:
            errors.append(f"s3:global:{self._error_code(exc)}")

        for region in regions:
            self._discover_ec2(session, account_id, region, resources, errors)
            self._discover_rds(session, region, resources, errors)
            self._discover_lambda(session, region, resources, errors)
            self._discover_ecs(session, region, resources, errors)

        return DiscoveryResult(resources=resources, errors=errors)

    def _discover_ec2(self, session, account_id, region, resources, errors):
        try:
            client = session.client("ec2", region_name=region, config=self.config)
            paginator = client.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        instance_id = str(instance.get("InstanceId", ""))
                        if not instance_id:
                            continue
                        tags = {
                            str(tag.get("Key")): str(tag.get("Value", ""))
                            for tag in instance.get("Tags", [])
                            if tag.get("Key")
                        }
                        resources.append(
                            ResourceRecord(
                                provider_resource_id=(
                                    f"ec2:{account_id}:{region}:{instance_id}"
                                ),
                                resource_type="aws.ec2.instance",
                                name=tags.get("Name", instance_id),
                                region=region,
                                state=str(instance.get("State", {}).get("Name", "")),
                                tags=tags,
                                metadata={
                                    "instance_type": str(instance.get("InstanceType", "")),
                                    "availability_zone": str(
                                        instance.get("Placement", {}).get(
                                            "AvailabilityZone", ""
                                        )
                                    ),
                                },
                            )
                        )
        except (ClientError, BotoCoreError) as exc:
            errors.append(f"ec2:{region}:{self._error_code(exc)}")

    def _discover_rds(self, session, region, resources, errors):
        try:
            client = session.client("rds", region_name=region, config=self.config)
            paginator = client.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for database in page.get("DBInstances", []):
                    resource_id = str(database.get("DBInstanceArn", ""))
                    if not resource_id:
                        continue
                    resources.append(
                        ResourceRecord(
                            provider_resource_id=resource_id,
                            resource_type="aws.rds.db_instance",
                            name=str(database.get("DBInstanceIdentifier", resource_id)),
                            region=region,
                            state=str(database.get("DBInstanceStatus", "")),
                            metadata={
                                "engine": str(database.get("Engine", "")),
                                "instance_class": str(database.get("DBInstanceClass", "")),
                                "multi_az": bool(database.get("MultiAZ", False)),
                            },
                        )
                    )
        except (ClientError, BotoCoreError) as exc:
            errors.append(f"rds:{region}:{self._error_code(exc)}")

    def _discover_lambda(self, session, region, resources, errors):
        try:
            client = session.client("lambda", region_name=region, config=self.config)
            paginator = client.get_paginator("list_functions")
            for page in paginator.paginate():
                for function in page.get("Functions", []):
                    resource_id = str(function.get("FunctionArn", ""))
                    if not resource_id:
                        continue
                    resources.append(
                        ResourceRecord(
                            provider_resource_id=resource_id,
                            resource_type="aws.lambda.function",
                            name=str(function.get("FunctionName", resource_id)),
                            region=region,
                            state="available",
                            metadata={
                                "runtime": str(function.get("Runtime", "")),
                                "memory_size": function.get("MemorySize"),
                                "timeout": function.get("Timeout"),
                            },
                        )
                    )
        except (ClientError, BotoCoreError) as exc:
            errors.append(f"lambda:{region}:{self._error_code(exc)}")

    def _discover_ecs(self, session, region, resources, errors):
        try:
            client = session.client("ecs", region_name=region, config=self.config)
            cluster_paginator = client.get_paginator("list_clusters")
            cluster_arns: list[str] = []
            for page in cluster_paginator.paginate():
                cluster_arns.extend(page.get("clusterArns", []))

            for cluster_arn in cluster_arns:
                cluster_name = str(cluster_arn).rsplit("/", 1)[-1]
                resources.append(
                    ResourceRecord(
                        provider_resource_id=str(cluster_arn),
                        resource_type="aws.ecs.cluster",
                        name=cluster_name,
                        region=region,
                        state="active",
                    )
                )
                service_paginator = client.get_paginator("list_services")
                for page in service_paginator.paginate(cluster=cluster_arn):
                    for service_arn in page.get("serviceArns", []):
                        service_name = str(service_arn).rsplit("/", 1)[-1]
                        resources.append(
                            ResourceRecord(
                                provider_resource_id=str(service_arn),
                                resource_type="aws.ecs.service",
                                name=service_name,
                                region=region,
                                state="active",
                                metadata={"cluster_arn": str(cluster_arn)},
                            )
                        )
        except (ClientError, BotoCoreError) as exc:
            errors.append(f"ecs:{region}:{self._error_code(exc)}")
