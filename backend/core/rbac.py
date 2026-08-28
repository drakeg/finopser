from rest_framework.permissions import SAFE_METHODS, BasePermission

from .entitlements import has_feature

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


class FeatureEntitlementPermission(BasePermission):
    message = "Your current subscription does not include this feature."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        feature = getattr(view, "required_feature", None)
        return bool(feature and has_feature(request.user, feature))


class ComplianceEntitlementPermission(FeatureEntitlementPermission):
    def has_permission(self, request, view):
        view.required_feature = "compliance"
        return super().has_permission(request, view)


class PolicyEntitlementPermission(FeatureEntitlementPermission):
    def has_permission(self, request, view):
        view.required_feature = "policies"
        return super().has_permission(request, view)


class BudgetEntitlementPermission(FeatureEntitlementPermission):
    def has_permission(self, request, view):
        view.required_feature = "budgets"
        return super().has_permission(request, view)


class RecommendationEntitlementPermission(FeatureEntitlementPermission):
    def has_permission(self, request, view):
        view.required_feature = "recommendations"
        return super().has_permission(request, view)


class RemediationEntitlementPermission(FeatureEntitlementPermission):
    def has_permission(self, request, view):
        feature = "remediation_live" if request.method not in SAFE_METHODS else "remediation_simulation"
        view.required_feature = feature
        return super().has_permission(request, view)
