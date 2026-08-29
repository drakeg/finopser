from .models import AuditEvent


def _organization_id(actor, obj):
    organization_id = getattr(obj, "organization_id", None)
    if organization_id is not None:
        return organization_id

    cloud_account = getattr(obj, "cloud_account", None)
    organization_id = getattr(cloud_account, "organization_id", None)
    if organization_id is not None:
        return organization_id

    budget = getattr(obj, "budget", None)
    organization_id = getattr(budget, "organization_id", None)
    if organization_id is not None:
        return organization_id

    resource = getattr(obj, "resource", None)
    resource_account = getattr(resource, "cloud_account", None)
    organization_id = getattr(resource_account, "organization_id", None)
    if organization_id is not None:
        return organization_id

    if getattr(actor, "is_authenticated", False) and not getattr(actor, "is_superuser", False):
        from .entitlements import user_organization

        organization = user_organization(actor)
        if organization is not None:
            return organization.id
    return None


def record_audit(actor, action: str, obj, metadata=None) -> AuditEvent:
    event_metadata = dict(metadata or {})
    organization_id = _organization_id(actor, obj)
    if organization_id is not None:
        event_metadata.setdefault("organization_id", organization_id)
    return AuditEvent.objects.create(
        organization_id=organization_id,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(getattr(obj, "pk", "")),
        object_repr=str(obj)[:255],
        metadata=event_metadata,
    )
