# AWS Account Onboarding

Finopser supports read-only AWS onboarding through STS AssumeRole. It does not accept or store IAM access-key/secret-key pairs.

## Trust role

Create an IAM role in the target account that trusts the AWS principal from which finopser will run. For cross-account production use, include an ExternalId condition. A representative trust policy is:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111122223333:role/finopser-runtime"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"sts:ExternalId": "replace-with-a-unique-value"}}
  }]
}
```

## Sprint 4 read-only inventory permissions

The target role may grant the specific discovery actions needed by the enabled inventory collectors rather than broad administrative access:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeRegions",
      "ec2:DescribeInstances",
      "rds:DescribeDBInstances",
      "s3:ListAllMyBuckets",
      "lambda:ListFunctions",
      "ecs:ListClusters",
      "ecs:ListServices"
    ],
    "Resource": "*"
  }]
}
```

Finopser treats service-level access failures as partial inventory results. Successful collectors are retained, errors are sanitized and recorded, and missing resources are not marked inactive after a partial run.

## Register the account

Create a cloud account through `/api/cloud-accounts/` with `provider=aws`, organization/project scope, the 12-digit AWS account ID, role ARN, and optional ExternalId. `external_id` is write-only in API responses.

## Validate

POST `/api/cloud-accounts/<id>/validate/`. Validation performs AssumeRole and GetCallerIdentity only. It does not modify AWS resources. The returned identity account must match the configured account ID.

## Inventory

After validation succeeds, POST `/api/cloud-accounts/<id>/sync-inventory/`. Sprint 4 discovery is explicit/manual and read-only. It covers EC2 instances, RDS DB instances, S3 buckets, Lambda functions, and ECS clusters/services. No sync occurs during Docker startup or ordinary page/API reads.

Validation and inventory failures persist only sanitized classifications. Temporary STS access key, secret key, and session token values are never stored.
