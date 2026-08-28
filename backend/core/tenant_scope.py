from rest_framework.exceptions import PermissionDenied

from .entitlements import organization_scope_id, user_organization


def scope_queryset(queryset, user, lookup="organization_id"):
    organization_id = organization_scope_id(user)
    if organization_id is None:
        return queryset
    return queryset.filter(**{lookup: organization_id})


def require_user_organization(user):
    organization = user_organization(user)
    if organization is None and not user.is_superuser:
        raise PermissionDenied("Complete organization setup before using this feature.")
    return organization


def validate_related_organization(user, *objects):
    organization = user_organization(user)
    if user.is_superuser or organization is None:
        return
    for obj in objects:
        if obj is None:
            continue
        object_organization_id = getattr(obj, "organization_id", None)
        if object_organization_id is None and hasattr(obj, "cloud_account"):
            object_organization_id = getattr(obj.cloud_account, "organization_id", None)
        if object_organization_id is not None and object_organization_id != organization.id:
            raise PermissionDenied("Referenced object must belong to your organization.")
