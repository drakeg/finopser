from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .account_models import OnboardingProfile, OrganizationMembership, Subscription
from .entitlements import entitlement_payload, user_organization
from .models import CloudAccount, Organization, OrganizationNode, Project


PLAN_CATALOG = [
    {
        "code": "free",
        "name": "Free",
        "description": "Core cloud inventory and cost visibility for a single AWS account.",
        "paid": False,
        "highlights": ["1 AWS account", "Inventory", "Cost dashboard"],
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Financial governance and security insights for growing environments.",
        "paid": True,
        "highlights": [
            "Up to 5 AWS accounts",
            "Budgets & forecasts",
            "Compliance & policies",
            "Recommendations",
            "Remediation simulation",
        ],
    },
    {
        "code": "business",
        "name": "Business",
        "description": "Team governance and approval-gated live remediation at larger scale.",
        "paid": True,
        "highlights": [
            "Up to 50 AWS accounts",
            "Everything in Pro",
            "Multi-user access",
            "Live allowlisted remediation",
        ],
    },
]


def _profile(user):
    profile, _ = OnboardingProfile.objects.get_or_create(user=user)
    return profile


def _next_step(profile):
    organization = profile.organization or user_organization(profile.user)
    if organization is None:
        return OnboardingProfile.Step.ORGANIZATION
    accounts = CloudAccount.objects.filter(organization=organization)
    if not accounts.exists():
        return OnboardingProfile.Step.CLOUD_ACCOUNT
    if not accounts.filter(status=CloudAccount.Status.VALID).exists():
        return OnboardingProfile.Step.VALIDATE
    if not accounts.filter(inventory_syncs__isnull=False).exists():
        return OnboardingProfile.Step.SYNC
    return OnboardingProfile.Step.COMPLETE


@api_view(["GET"])
def plan_catalog(request):
    return Response({"plans": PLAN_CATALOG, "billing_provider_configured": False})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bootstrap(request):
    profile = _profile(request.user)
    step = _next_step(profile)
    if profile.current_step != step:
        profile.current_step = step
        if step == OnboardingProfile.Step.COMPLETE and profile.completed_at is None:
            profile.completed_at = timezone.now()
        profile.save(update_fields=["current_step", "completed_at", "updated_at"])
    organization = profile.organization or user_organization(request.user)
    payload = {
        "onboarding": {
            "required": step != OnboardingProfile.Step.COMPLETE,
            "current_step": step,
            "completed_at": profile.completed_at,
        },
        "organization": None,
        "subscription": None,
        "cloud_accounts": [],
    }
    if organization is not None:
        payload["organization"] = {"id": organization.id, "name": organization.name}
        payload["subscription"] = entitlement_payload(organization)
        payload["cloud_accounts"] = list(
            CloudAccount.objects.filter(organization=organization)
            .order_by("name")
            .values("id", "name", "provider", "provider_account_id", "status", "last_error")
        )
    return Response(payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_organization(request):
    profile = _profile(request.user)
    if profile.organization_id or user_organization(request.user):
        return Response(
            {"detail": "This account is already attached to an organization."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    name = str(request.data.get("name", "")).strip()
    if not name:
        return Response(
            {"detail": "Organization name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if Organization.objects.filter(name__iexact=name).exists():
        return Response(
            {"detail": "That organization name is already in use."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    with transaction.atomic():
        organization = Organization.objects.create(name=name)
        root = OrganizationNode.objects.create(
            organization=organization,
            name="Root",
            node_type=OrganizationNode.NodeType.OTHER,
        )
        Project.objects.create(
            organization=organization,
            node=root,
            name="Default",
            owner=request.user.get_username(),
        )
        OrganizationMembership.objects.create(
            user=request.user,
            organization=organization,
            role=OrganizationMembership.Role.OWNER,
        )
        Subscription.objects.create(organization=organization)
        profile.organization = organization
        profile.current_step = OnboardingProfile.Step.CLOUD_ACCOUNT
        profile.save(update_fields=["organization", "current_step", "updated_at"])
    return Response(
        {
            "organization": {"id": organization.id, "name": organization.name},
            "subscription": entitlement_payload(organization),
            "next_step": profile.current_step,
        },
        status=status.HTTP_201_CREATED,
    )
