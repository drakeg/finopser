import hashlib
import json

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from django.utils import timezone

from .audit import record_audit
from .automation_models import RemediationAction, RemediationEvent
from .notifications import notify
from .providers.aws import AWSProvider

ACTION_ADD_TAGS = "aws.add_tags"
SUPPORTED_TAG_RESOURCE_TYPES = {
    "aws.ec2.instance",
    "aws.rds.db_instance",
    "aws.lambda.function",
    "aws.ecs.cluster",
    "aws.ecs.service",
}
ACTION_REGISTRY = {
    ACTION_ADD_TAGS: {
        "label": "Add or update resource tags",
        "risk": "low",
        "supported_resource_types": sorted(SUPPORTED_TAG_RESOURCE_TYPES),
    }
}


class RemediationError(Exception):
    pass


class StaleEvidenceError(RemediationError):
    pass


def _event(action, event_type, actor=None, metadata=None):
    return RemediationEvent.objects.create(
        action=action,
        event_type=event_type,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        metadata=metadata or {},
    )


def _notify_remediation(action, *, state, severity, title, detail):
    return notify(
        action.cloud_account.organization,
        dedupe_key=f"remediation:{action.id}:{state}",
        category="remediation",
        severity=severity,
        title=title,
        detail=detail,
        target="Automation",
        object_type="remediation_action",
        object_id=str(action.id),
    )


def _validate_parameters(action):
    if action.action_key != ACTION_ADD_TAGS:
        raise RemediationError("Action is not allowlisted.")
    if action.resource.resource_type not in SUPPORTED_TAG_RESOURCE_TYPES:
        raise RemediationError("Resource type is not supported by this action.")
    tags = action.parameters.get("tags") if isinstance(action.parameters, dict) else None
    if not isinstance(tags, dict) or not tags:
        raise RemediationError("A non-empty tags object is required.")
    cleaned = {}
    for key, value in tags.items():
        key = str(key).strip()
        value = str(value)
        if not key:
            raise RemediationError("Tag keys cannot be empty.")
        if key.lower().startswith("aws:"):
            raise RemediationError("Reserved aws: tag keys are not allowed.")
        if len(key) > 128 or len(value) > 256:
            raise RemediationError("Tag key or value exceeds AWS limits.")
        cleaned[key] = value
    return {"tags": cleaned}


def evidence_fingerprint(action):
    resource = action.resource
    payload = {
        "provider_resource_id": resource.provider_resource_id,
        "resource_type": resource.resource_type,
        "region": resource.region,
        "state": resource.state,
        "is_active": resource.is_active,
        "last_seen": resource.last_seen.isoformat(),
        "tags": resource.tags or {},
        "parameters": _validate_parameters(action),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def preview_action(action, actor=None):
    if action.status not in {RemediationAction.Status.REQUESTED, RemediationAction.Status.PREVIEWED}:
        raise RemediationError("Only requested actions can be previewed.")
    params = _validate_parameters(action)
    current_tags = dict(action.resource.tags or {})
    desired_tags = {**current_tags, **params["tags"]}
    changed = {
        key: {"from": current_tags.get(key), "to": value}
        for key, value in params["tags"].items()
        if current_tags.get(key) != value
    }
    fingerprint = evidence_fingerprint(action)
    action.preview = {
        "action": ACTION_REGISTRY[action.action_key]["label"],
        "risk": ACTION_REGISTRY[action.action_key]["risk"],
        "resource_id": action.resource.provider_resource_id,
        "resource_type": action.resource.resource_type,
        "region": action.resource.region,
        "current_tags": current_tags,
        "requested_tags": params["tags"],
        "resulting_tags": desired_tags,
        "changes": changed,
        "simulation": action.simulation,
        "provider_mutation": False,
    }
    action.evidence_fingerprint = fingerprint
    action.status = RemediationAction.Status.PREVIEWED
    action.error = ""
    action.save(update_fields=["preview", "evidence_fingerprint", "status", "error", "updated_at"])
    _event(action, "previewed", actor, {"fingerprint": fingerprint, "changes": changed})
    record_audit(actor, "remediation.preview", action, {"simulation": action.simulation})
    _notify_remediation(
        action,
        state="approval",
        severity="warning",
        title=f"Remediation approval required: {action.resource.name or action.resource.provider_resource_id}",
        detail="A remediation preview is ready and requires an administrator decision before execution.",
    )
    return action


def approve_action(action, actor):
    if action.status != RemediationAction.Status.PREVIEWED:
        raise RemediationError("Action must be previewed before approval.")
    action.status = RemediationAction.Status.APPROVED
    action.approved_by = actor
    action.approved_at = timezone.now()
    action.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    _event(action, "approved", actor, {"fingerprint": action.evidence_fingerprint})
    record_audit(actor, "remediation.approve", action)
    return action


def reject_action(action, actor):
    if action.status not in {RemediationAction.Status.REQUESTED, RemediationAction.Status.PREVIEWED}:
        raise RemediationError("Only pending actions can be rejected.")
    action.status = RemediationAction.Status.REJECTED
    action.save(update_fields=["status", "updated_at"])
    _event(action, "rejected", actor)
    record_audit(actor, "remediation.reject", action)
    return action


def _extract_ec2_instance_id(provider_resource_id):
    return provider_resource_id.rsplit(":", 1)[-1]


def _apply_aws_tags(action, tags):
    account = action.cloud_account
    provider = AWSProvider()
    session = provider._assumed_session(
        role_arn=account.role_arn,
        external_id=account.external_id,
        session_name="finopser-remediation-tags",
    )
    resource = action.resource
    if resource.resource_type == "aws.ec2.instance":
        client = session.client("ec2", region_name=resource.region, config=provider.config)
        client.create_tags(
            Resources=[_extract_ec2_instance_id(resource.provider_resource_id)],
            Tags=[{"Key": key, "Value": value} for key, value in sorted(tags.items())],
        )
    elif resource.resource_type == "aws.rds.db_instance":
        client = session.client("rds", region_name=resource.region, config=provider.config)
        client.add_tags_to_resource(
            ResourceName=resource.provider_resource_id,
            Tags=[{"Key": key, "Value": value} for key, value in sorted(tags.items())],
        )
    elif resource.resource_type == "aws.lambda.function":
        client = session.client("lambda", region_name=resource.region, config=provider.config)
        client.tag_resource(Resource=resource.provider_resource_id, Tags=tags)
    elif resource.resource_type in {"aws.ecs.cluster", "aws.ecs.service"}:
        client = session.client("ecs", region_name=resource.region, config=provider.config)
        client.tag_resource(
            resourceArn=resource.provider_resource_id,
            tags=[{"key": key, "value": value} for key, value in sorted(tags.items())],
        )
    else:
        raise RemediationError("Resource type is not supported by this action.")


def execute_action(action, actor):
    if action.status != RemediationAction.Status.APPROVED:
        raise RemediationError("Action must be explicitly approved before execution.")
    current_fingerprint = evidence_fingerprint(action)
    if not action.evidence_fingerprint or current_fingerprint != action.evidence_fingerprint:
        action.status = RemediationAction.Status.STALE
        action.error = "Persisted resource evidence changed after preview; preview and approval are required again."
        action.save(update_fields=["status", "error", "updated_at"])
        _event(
            action,
            "stale",
            actor,
            {"expected": action.evidence_fingerprint, "current": current_fingerprint},
        )
        record_audit(actor, "remediation.stale", action)
        _notify_remediation(
            action,
            state="stale",
            severity="high",
            title=f"Remediation needs a new preview: {action.resource.name or action.resource.provider_resource_id}",
            detail=action.error,
        )
        raise StaleEvidenceError(action.error)

    tags = _validate_parameters(action)["tags"]
    action.executed_by = actor
    action.executed_at = timezone.now()
    try:
        if action.simulation:
            result = {"simulation": True, "mutated": False, "tags": tags}
        else:
            _apply_aws_tags(action, tags)
            result = {"simulation": False, "mutated": True, "tags": tags}
            action.resource.tags = {**(action.resource.tags or {}), **tags}
            action.resource.save(update_fields=["tags"])
        action.status = RemediationAction.Status.SUCCEEDED
        action.provider_result = result
        action.error = ""
        action.save(
            update_fields=[
                "status",
                "provider_result",
                "error",
                "executed_by",
                "executed_at",
                "updated_at",
            ]
        )
        _event(action, "executed", actor, result)
        record_audit(actor, "remediation.execute", action, result)
        _notify_remediation(
            action,
            state="succeeded",
            severity="info",
            title=f"Remediation succeeded: {action.resource.name or action.resource.provider_resource_id}",
            detail=(
                "Remediation simulation completed successfully; no provider mutation was made."
                if action.simulation
                else "The approved remediation completed successfully."
            ),
        )
        return action
    except (ClientError, BotoCoreError, NoCredentialsError, KeyError, RemediationError) as exc:
        action.status = RemediationAction.Status.FAILED
        action.error = f"{exc.__class__.__name__}: {str(exc)[:180]}"
        action.save(
            update_fields=["status", "error", "executed_by", "executed_at", "updated_at"]
        )
        _event(action, "failed", actor, {"error": action.error})
        record_audit(actor, "remediation.failed", action, {"error": action.error})
        _notify_remediation(
            action,
            state="failed",
            severity="critical",
            title=f"Remediation failed: {action.resource.name or action.resource.provider_resource_id}",
            detail=action.error,
        )
        raise RemediationError(action.error) from exc
