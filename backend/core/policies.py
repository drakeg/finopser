from django.utils import timezone

from .audit import record_audit
from .models import CloudResource, GovernancePolicy, PolicyRun, PolicyViolation

BUILTIN_POLICIES = [
    {
        "code": "GUARD-EC2-PUBLIC-IP",
        "name": "Restrict public EC2 IPv4 exposure",
        "description": "Reports active EC2 instances with a persisted public IPv4 address.",
        "severity": GovernancePolicy.Severity.HIGH,
        "mode": GovernancePolicy.Mode.OBSERVE,
        "resource_type": "aws.ec2.instance",
        "rule_key": "ec2_public_ipv4",
    },
    {
        "code": "GUARD-RDS-PUBLIC",
        "name": "Restrict public RDS accessibility",
        "description": "Reports RDS instances whose persisted PubliclyAccessible value is true.",
        "severity": GovernancePolicy.Severity.HIGH,
        "mode": GovernancePolicy.Mode.OBSERVE,
        "resource_type": "aws.rds.db_instance",
        "rule_key": "rds_public_access",
    },
    {
        "code": "GUARD-RDS-ENCRYPTION",
        "name": "Require RDS storage encryption",
        "description": "Reports RDS instances whose persisted StorageEncrypted value is false.",
        "severity": GovernancePolicy.Severity.HIGH,
        "mode": GovernancePolicy.Mode.RECOMMEND,
        "resource_type": "aws.rds.db_instance",
        "rule_key": "rds_storage_encryption",
    },
]


def ensure_builtin_policies():
    policies = []
    for definition in BUILTIN_POLICIES:
        policy, _ = GovernancePolicy.objects.get_or_create(
            code=definition["code"],
            defaults=definition,
        )
        policies.append(policy)
    return policies


def _evaluate_rule(policy, resource):
    metadata = resource.metadata or {}
    if policy.rule_key == "ec2_public_ipv4":
        if "public_ip_address" not in metadata:
            return "unknown", {"reason": "public_ip_address evidence not present"}
        value = str(metadata.get("public_ip_address") or "")
        return ("violation" if value else "pass"), {"public_ip_address": value}
    if policy.rule_key == "rds_public_access":
        if "publicly_accessible" not in metadata:
            return "unknown", {"reason": "publicly_accessible evidence not present"}
        value = bool(metadata.get("publicly_accessible"))
        return ("violation" if value else "pass"), {"publicly_accessible": value}
    if policy.rule_key == "rds_storage_encryption":
        if "storage_encrypted" not in metadata:
            return "unknown", {"reason": "storage_encrypted evidence not present"}
        value = bool(metadata.get("storage_encrypted"))
        return ("pass" if value else "violation"), {"storage_encrypted": value}
    return "unknown", {"reason": "unsupported policy rule"}


def _resources_for_policy(policy):
    queryset = CloudResource.objects.filter(is_active=True, resource_type=policy.resource_type).select_related(
        "cloud_account",
        "cloud_account__project",
        "cloud_account__project__node",
    )
    if policy.organization_id:
        queryset = queryset.filter(cloud_account__organization_id=policy.organization_id)
    if policy.node_id:
        queryset = queryset.filter(cloud_account__project__node_id=policy.node_id)
    if policy.project_id:
        queryset = queryset.filter(cloud_account__project_id=policy.project_id)
    if policy.cloud_account_id:
        queryset = queryset.filter(cloud_account_id=policy.cloud_account_id)
    return queryset


def evaluate_policies(actor=None):
    now = timezone.now()
    run = PolicyRun.objects.create(started_at=now)
    ensure_builtin_policies()
    passed = violated = unknown = resolved = 0

    for policy in GovernancePolicy.objects.filter(enabled=True).order_by("code"):
        for resource in _resources_for_policy(policy):
            result, evidence = _evaluate_rule(policy, resource)
            evidence = {
                **evidence,
                "mode": policy.mode,
                "resource_id": resource.provider_resource_id,
                "resource_type": resource.resource_type,
                "region": resource.region,
            }
            violation = PolicyViolation.objects.filter(policy=policy, resource=resource).first()
            if result == "unknown":
                unknown += 1
                continue
            if result == "pass":
                passed += 1
                if violation and violation.status != PolicyViolation.Status.RESOLVED:
                    violation.status = PolicyViolation.Status.RESOLVED
                    violation.last_seen = now
                    violation.resolved_at = now
                    violation.evidence = evidence
                    violation.save(update_fields=["status", "last_seen", "resolved_at", "evidence"])
                    resolved += 1
                continue

            violated += 1
            defaults = {
                "cloud_account": resource.cloud_account,
                "severity": policy.severity,
                "status": PolicyViolation.Status.OPEN,
                "evidence": evidence,
                "last_seen": now,
                "resolved_at": None,
            }
            if violation:
                for key, value in defaults.items():
                    setattr(violation, key, value)
                violation.save()
            else:
                PolicyViolation.objects.create(
                    policy=policy,
                    resource=resource,
                    first_seen=now,
                    **defaults,
                )

    run.completed_at = timezone.now()
    run.passed_count = passed
    run.violated_count = violated
    run.unknown_count = unknown
    run.resolved_count = resolved
    run.save()
    if actor is not None:
        record_audit(
            actor,
            "policy.evaluate",
            run,
            {"passed": passed, "violated": violated, "unknown": unknown, "resolved": resolved},
        )
    return run
