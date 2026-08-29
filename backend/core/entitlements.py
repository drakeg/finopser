from dataclasses import dataclass

from .account_models import OnboardingProfile, OrganizationMembership, Subscription
from .models import CloudAccount


@dataclass(frozen=True)
class PlanEntitlements:
    max_cloud_accounts: int
    budgets: bool
    compliance: bool
    policies: bool
    recommendations: bool
    remediation_simulation: bool
    remediation_live: bool
    multi_user: bool


PLAN_ENTITLEMENTS = {
    Subscription.Plan.FREE: PlanEntitlements(
        max_cloud_accounts=1,
        budgets=False,
        compliance=False,
        policies=False,
        recommendations=False,
        remediation_simulation=False,
        remediation_live=False,
        multi_user=False,
    ),
    Subscription.Plan.PRO: PlanEntitlements(
        max_cloud_accounts=5,
        budgets=True,
        compliance=True,
        policies=True,
        recommendations=True,
        remediation_simulation=True,
        remediation_live=False,
        multi_user=False,
    ),
    Subscription.Plan.BUSINESS: PlanEntitlements(
        max_cloud_accounts=50,
        budgets=True,
        compliance=True,
        policies=True,
        recommendations=True,
        remediation_simulation=True,
        remediation_live=True,
        multi_user=True,
    ),
}

PAID_ACCESS_STATUSES = {
    Subscription.Status.TRIALING,
    Subscription.Status.ACTIVE,
    Subscription.Status.PAST_DUE,
}


def user_organization(user):
    if not user or not user.is_authenticated:
        return None
    membership = (
        OrganizationMembership.objects.select_related("organization")
        .filter(user=user)
        .order_by("id")
        .first()
    )
    return membership.organization if membership else None


def organization_scope_id(user):
    """Return an org id for self-service users, -1 before setup, or None for legacy/global users."""
    if not user or not user.is_authenticated:
        return -1
    if user.is_superuser:
        return None
    organization = user_organization(user)
    if organization is not None:
        return organization.id
    if OnboardingProfile.objects.filter(user=user).exists():
        return -1
    return None


def organization_subscription(organization):
    subscription, _ = Subscription.objects.get_or_create(organization=organization)
    return subscription


def effective_plan(subscription: Subscription) -> str:
    if subscription.plan == Subscription.Plan.FREE:
        return Subscription.Plan.FREE
    if subscription.status in PAID_ACCESS_STATUSES:
        return subscription.plan
    return Subscription.Plan.FREE


def entitlement_payload(organization):
    subscription = organization_subscription(organization)
    active_plan = effective_plan(subscription)
    entitlements = PLAN_ENTITLEMENTS[active_plan]
    cloud_account_count = CloudAccount.objects.filter(organization=organization).count()
    return {
        "plan": subscription.plan,
        "effective_plan": active_plan,
        "status": subscription.status,
        "billing_configured": bool(subscription.billing_provider),
        "max_cloud_accounts": entitlements.max_cloud_accounts,
        "usage": {
            "cloud_accounts": cloud_account_count,
            "cloud_accounts_over_limit": max(cloud_account_count - entitlements.max_cloud_accounts, 0),
        },
        "over_limit": cloud_account_count > entitlements.max_cloud_accounts,
        "features": {
            "inventory": True,
            "costs": True,
            "budgets": entitlements.budgets,
            "compliance": entitlements.compliance,
            "policies": entitlements.policies,
            "recommendations": entitlements.recommendations,
            "remediation_simulation": entitlements.remediation_simulation,
            "remediation_live": entitlements.remediation_live,
            "multi_user": entitlements.multi_user,
        },
    }


def has_feature(user, feature: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    organization = user_organization(user)
    if organization is None:
        return False
    payload = entitlement_payload(organization)
    return bool(payload["features"].get(feature, False))
