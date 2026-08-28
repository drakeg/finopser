from rest_framework.permissions import SAFE_METHODS, BasePermission

PLATFORM_ADMIN = "Platform Administrator"
CLOUD_ADMIN = "Cloud Administrator"
FINOPS_ANALYST = "FinOps Analyst"
SECURITY_ENGINEER = "Security / Compliance Engineer"
PROJECT_OWNER = "Project Owner"
AUDITOR = "Auditor"

MANAGED_ROLES = [PLATFORM_ADMIN, CLOUD_ADMIN, FINOPS_ANALYST, SECURITY_ENGINEER, PROJECT_OWNER, AUDITOR]
MANAGER_ROLES = {PLATFORM_ADMIN, CLOUD_ADMIN}


def user_has_role(user, role_names) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    memberships = getattr(user, "organization_memberships", None)
    if memberships is not None and memberships.filter(role__in=["owner", "admin"]).exists():
        return True
    return user.groups.filter(name__in=role_names).exists()


class GovernancePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(request.user, MANAGER_ROLES)


class PlatformAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return user_has_role(request.user, {PLATFORM_ADMIN})
