# AWS Account Onboarding

Sprint 3 supports read-only identity validation through AWS STS AssumeRole. finopser does not accept or store IAM access-key/secret-key pairs.

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

Sprint 3 requires only enough target-role permission for `sts:GetCallerIdentity` after assumption. Future inventory/FinOps sprints will document additional read-only permissions separately rather than broadening this role preemptively.

## Register the account

Create a cloud account through `/api/cloud-accounts/` with `provider=aws`, organization/project scope, the 12-digit AWS account ID, role ARN, and optional ExternalId. `external_id` is write-only in API responses.

## Validate

POST `/api/cloud-accounts/<id>/validate/`. Validation performs AssumeRole and GetCallerIdentity only. It does not modify AWS resources. The returned identity account must match the configured account ID.

Validation failures persist only a sanitized error classification. Temporary STS access key, secret key, and session token values are never stored.
