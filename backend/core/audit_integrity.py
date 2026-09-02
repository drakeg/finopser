import hashlib
import json

from django.db.models import QuerySet

from .audit import record_audit
from .models import AuditEvent, Organization
from .tenant_scope import scope_queryset

CHECKPOINT_ACTION = "audit.integrity.checkpoint"
CHECKPOINT_ALGORITHM = "sha256"


def audit_evidence_queryset(user) -> QuerySet:
    if getattr(user, "is_superuser", False):
        return AuditEvent.objects.filter(organization__isnull=True).order_by("id")
    return scope_queryset(AuditEvent.objects.all(), user).order_by("id")


def _canonical_event(event: AuditEvent) -> bytes:
    payload = {
        "id": event.id,
        "organization_id": event.organization_id,
        "actor_id": event.actor_id,
        "action": event.action,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "object_repr": event.object_repr,
        "metadata": event.metadata,
        "created_at": event.created_at.isoformat(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def calculate_digest(events) -> tuple[str, int, int | None]:
    digest = hashlib.sha256()
    count = 0
    through_event_id = None
    for event in events:
        digest.update(_canonical_event(event))
        digest.update(b"\n")
        count += 1
        through_event_id = event.id
    return digest.hexdigest(), count, through_event_id


def create_checkpoint(user) -> AuditEvent:
    queryset = audit_evidence_queryset(user)
    digest, event_count, through_event_id = calculate_digest(queryset)

    if getattr(user, "is_superuser", False):
        target = Organization(name="platform-audit-scope")
        target.pk = None
    else:
        from .entitlements import user_organization

        target = user_organization(user)
        if target is None:
            raise ValueError("User does not have an organization audit scope.")

    return record_audit(
        user,
        CHECKPOINT_ACTION,
        target,
        {
            "algorithm": CHECKPOINT_ALGORITHM,
            "digest": digest,
            "event_count": event_count,
            "through_event_id": through_event_id,
            "scope": "platform" if getattr(user, "is_superuser", False) else "organization",
        },
    )


def verify_latest_checkpoint(user) -> dict:
    scoped = audit_evidence_queryset(user)
    checkpoint = scoped.filter(action=CHECKPOINT_ACTION).order_by("-id").first()
    if checkpoint is None:
        return {
            "status": "unverified",
            "valid": None,
            "algorithm": CHECKPOINT_ALGORITHM,
            "checkpoint_event_id": None,
            "through_event_id": None,
            "event_count": 0,
            "unchecked_event_count": scoped.count(),
        }

    metadata = checkpoint.metadata or {}
    through_event_id = metadata.get("through_event_id")
    expected_digest = metadata.get("digest", "")
    expected_count = metadata.get("event_count")
    if through_event_id is None:
        events = scoped.none()
        uncovered = scoped.exclude(id=checkpoint.id)
    else:
        events = scoped.filter(id__lte=through_event_id)
        uncovered = scoped.filter(id__gt=through_event_id).exclude(id=checkpoint.id)
    actual_digest, actual_count, _ = calculate_digest(events)
    valid = (
        metadata.get("algorithm") == CHECKPOINT_ALGORITHM
        and expected_digest == actual_digest
        and expected_count == actual_count
    )
    return {
        "status": "valid" if valid else "invalid",
        "valid": valid,
        "algorithm": CHECKPOINT_ALGORITHM,
        "checkpoint_event_id": checkpoint.id,
        "through_event_id": through_event_id,
        "event_count": actual_count,
        "unchecked_event_count": uncovered.count(),
    }
