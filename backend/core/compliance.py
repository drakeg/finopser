from django.db.models import Q
from django.utils import timezone

from .audit import record_audit
from .entitlements import organization_scope_id
from .models import (
    CloudResource,
    ComplianceControl,
    ComplianceException,
    ComplianceFinding,
    ComplianceFramework,
    ComplianceRun,
)
from .notifications import notify

FRAMEWORK_CODE = "FINOPSER-AWS-BASELINE"
CONTROL_DEFINITIONS = [
    {
        "code": "AWS-EC2-001",
        "title": "EC2 instances should not have a public IPv4 address",
        "description": "Flags active EC2 instances with a persisted public IPv4 address.",
        "severity": ComplianceControl.Severity.HIGH,
        "resource_type": "aws.ec2.instance",
        "check_key": "ec2_public_ipv4",
    },
    {
        "code": "AWS-RDS-001",
        "title": "RDS instances should not be publicly accessible",
        "description": "Flags RDS instances whose persisted PubliclyAccessible value is true.",
        "severity": ComplianceControl.Severity.HIGH,
        "resource_type": "aws.rds.db_instance",
        "check_key": "rds_public_access",
    },
    {
        "code": "AWS-RDS-002",
        "title": "RDS storage should be encrypted",
        "description": "Flags RDS instances whose persisted StorageEncrypted value is false.",
        "severity": ComplianceControl.Severity.HIGH,
        "resource_type": "aws.rds.db_instance",
        "check_key": "rds_storage_encryption",
    },
]


def ensure_baseline_controls():
    framework, _ = ComplianceFramework.objects.update_or_create(
        code=FRAMEWORK_CODE,
        defaults={
            "name": "Finopser AWS Baseline",
            "version": "1.0",
            "description": "Initial evidence-backed AWS compliance baseline.",
            "enabled": True,
        },
    )
    controls = []
    for definition in CONTROL_DEFINITIONS:
        control, _ = ComplianceControl.objects.update_or_create(
            framework=framework,
            code=definition["code"],
            defaults={key: value for key, value in definition.items() if key != "code"},
        )
        controls.append(control)
    return controls


def _evaluate_control(control, resource):
    metadata = resource.metadata or {}
    if control.check_key == "ec2_public_ipv4":
        if "public_ip_address" not in metadata:
            return "unknown", {"reason": "public_ip_address evidence not present"}
        public_ip = str(metadata.get("public_ip_address") or "")
        return ("fail" if public_ip else "pass"), {"public_ip_address": public_ip}
    if control.check_key == "rds_public_access":
        if "publicly_accessible" not in metadata:
            return "unknown", {"reason": "publicly_accessible evidence not present"}
        value = bool(metadata.get("publicly_accessible"))
        return ("fail" if value else "pass"), {"publicly_accessible": value}
    if control.check_key == "rds_storage_encryption":
        if "storage_encrypted" not in metadata:
            return "unknown", {"reason": "storage_encrypted evidence not present"}
        value = bool(metadata.get("storage_encrypted"))
        return ("pass" if value else "fail"), {"storage_encrypted": value}
    return "unknown", {"reason": "unsupported control"}


def _exception_for(control, resource, now, organization_id=None):
    queryset = ComplianceException.objects.filter(control=control, is_active=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    if organization_id is not None:
        queryset = queryset.filter(
            Q(resource__cloud_account__organization_id=organization_id)
            | Q(resource__isnull=True, cloud_account__organization_id=organization_id)
        )
    return (
        queryset.filter(
            Q(resource=resource)
            | Q(resource__isnull=True, cloud_account=resource.cloud_account)
            | Q(resource__isnull=True, cloud_account__isnull=True)
        )
        .first()
    )


def evaluate_compliance(actor=None):
    now = timezone.now()
    organization_id = organization_scope_id(actor) if actor is not None else None
    run = ComplianceRun.objects.create(
        started_at=now,
        organization_id=organization_id if organization_id not in {None, -1} else None,
    )
    controls = ensure_baseline_controls()
    passed = failed = unknown = resolved = 0

    for control in controls:
        resources = CloudResource.objects.filter(
            is_active=True,
            resource_type=control.resource_type,
        ).select_related("cloud_account")
        if organization_id is not None:
            resources = resources.filter(cloud_account__organization_id=organization_id)
        for resource in resources:
            result, evidence = _evaluate_control(control, resource)
            evidence = {
                **evidence,
                "resource_id": resource.provider_resource_id,
                "resource_type": resource.resource_type,
                "region": resource.region,
            }
            finding = ComplianceFinding.objects.filter(control=control, resource=resource).first()

            if result == "unknown":
                unknown += 1
                continue

            if result == "pass":
                passed += 1
                if finding and finding.status != ComplianceFinding.Status.RESOLVED:
                    finding.status = ComplianceFinding.Status.RESOLVED
                    finding.last_seen = now
                    finding.resolved_at = now
                    finding.evidence = evidence
                    finding.save(update_fields=["status", "last_seen", "resolved_at", "evidence"])
                    resolved += 1
                continue

            failed += 1
            exception = _exception_for(control, resource, now, organization_id)
            finding_status = (
                ComplianceFinding.Status.EXCEPTED
                if exception
                else ComplianceFinding.Status.OPEN
            )
            defaults = {
                "cloud_account": resource.cloud_account,
                "severity": control.severity,
                "status": finding_status,
                "evidence": evidence,
                "last_seen": now,
                "resolved_at": None,
            }
            if finding:
                for key, value in defaults.items():
                    setattr(finding, key, value)
                finding.save()
            else:
                ComplianceFinding.objects.create(
                    control=control,
                    resource=resource,
                    first_seen=now,
                    **defaults,
                )

    run.completed_at = timezone.now()
    run.passed_count = passed
    run.failed_count = failed
    run.unknown_count = unknown
    run.resolved_count = resolved
    run.save()
    if run.organization_id and failed:
        notify(
            run.organization,
            dedupe_key="compliance:open-failures",
            category="compliance",
            severity="high",
            title="Compliance findings need attention",
            detail=f"Latest evaluation found {failed} failing checks; {resolved} were resolved.",
            target="Compliance",
            object_type="ComplianceRun",
            object_id=str(run.id),
        )
    if actor is not None:
        record_audit(
            actor,
            "compliance.evaluate",
            run,
            {
                "passed": passed,
                "failed": failed,
                "unknown": unknown,
                "resolved": resolved,
                "organization_id": organization_id,
            },
        )
    return run
