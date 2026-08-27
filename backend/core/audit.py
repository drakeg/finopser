from .models import AuditEvent


def record_audit(actor, action: str, obj, metadata=None) -> AuditEvent:
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(getattr(obj, "pk", "")),
        object_repr=str(obj)[:255],
        metadata=metadata or {},
    )
