from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .account_models import OnboardingProfile, OrganizationMembership, Subscription
from .audit import record_audit
from .costs import sync_costs
from .entitlements import entitlement_payload, organization_subscription, user_organization
from .inventory import sync_inventory
from .models import CloudAccount, CostSync, InventorySync, Organization, OrganizationNode, Project
from .providers import ProviderValidationError, get_provider


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


def _organization_for_user(user):
    profile = _profile(user)
    return profile.organization or user_organization(user)


def _next_step(profile):
    organization = profile.organization or user_organization(profile.user)
    if organization is None:
        return OnboardingProfile.Step.ORGANIZATION
    accounts = CloudAccount.objects.filter(organization=organization)
    if not accounts.exists():
        return OnboardingProfile.Step.CLOUD_ACCOUNT
    valid_accounts = accounts.filter(status=CloudAccount.Status.VALID)
    if not valid_accounts.exists():
        return OnboardingProfile.Step.VALIDATE
    synced = valid_accounts.filter(
        inventory_syncs__status__in=[InventorySync.Status.SUCCESS, InventorySync.Status.PARTIAL],
        cost_syncs__status__in=[CostSync.Status.SUCCESS, CostSync.Status.PARTIAL],
    ).distinct()
    if not synced.exists():
        return OnboardingProfile.Step.SYNC
    return OnboardingProfile.Step.COMPLETE


def _refresh_profile(profile):
    step = _next_step(profile)
    profile.current_step = step
    if step == OnboardingProfile.Step.COMPLETE and profile.completed_at is None:
        profile.completed_at = timezone.now()
    profile.save(update_fields=["current_step", "completed_at", "updated_at"])
    return step


@api_view(["GET"])
def plan_catalog(request):
    return Response({"plans": PLAN_CATALOG, "billing_provider_configured": False})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bootstrap(request):
    profile = _profile(request.user)
    step = _refresh_profile(profile)
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
    record_audit(request.user, "onboarding.organization.create", organization)
    return Response(
        {
            "organization": {"id": organization.id, "name": organization.name},
            "subscription": entitlement_payload(organization),
            "next_step": profile.current_step,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def connect_cloud_account(request):
    organization = _organization_for_user(request.user)
    if organization is None:
        return Response(
            {"detail": "Create your organization first."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    subscription = organization_subscription(organization)
    limits = entitlement_payload(organization)
    if CloudAccount.objects.filter(organization=organization).count() >= limits["max_cloud_accounts"]:
        return Response(
            {
                "detail": (
                    f"Your {subscription.get_plan_display()} plan allows "
                    f"{limits['max_cloud_accounts']} cloud account(s). Upgrade to add more."
                ),
                "upgrade_required": True,
            },
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )
    name = str(request.data.get("name", "")).strip()
    account_id = str(request.data.get("provider_account_id", "")).strip()
    role_arn = str(request.data.get("role_arn", "")).strip()
    external_id = str(request.data.get("external_id", "")).strip()
    if not name or not account_id or not role_arn:
        return Response(
            {"detail": "Account name, AWS account ID, and role ARN are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not account_id.isdigit() or len(account_id) != 12:
        return Response(
            {"detail": "AWS account ID must be exactly 12 digits."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if CloudAccount.objects.filter(provider="aws", provider_account_id=account_id).exists():
        return Response(
            {"detail": "That AWS account is already connected."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    project = Project.objects.filter(organization=organization).order_by("id").first()
    account = CloudAccount.objects.create(
        provider=CloudAccount.Provider.AWS,
        organization=organization,
        project=project,
        name=name,
        provider_account_id=account_id,
        role_arn=role_arn,
        external_id=external_id,
    )
    profile = _profile(request.user)
    profile.current_step = OnboardingProfile.Step.VALIDATE
    profile.save(update_fields=["current_step", "updated_at"])
    record_audit(request.user, "onboarding.cloud_account.create", account)
    return Response(
        {
            "id": account.id,
            "name": account.name,
            "provider_account_id": account.provider_account_id,
            "status": account.status,
            "next_step": profile.current_step,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_cloud_account(request, pk: int):
    organization = _organization_for_user(request.user)
    try:
        account = CloudAccount.objects.get(pk=pk, organization=organization)
    except CloudAccount.DoesNotExist:
        return Response({"detail": "Cloud account not found."}, status=status.HTTP_404_NOT_FOUND)
    provider = get_provider(account.provider)
    try:
        result = provider.validate_account(
            account_id=account.provider_account_id,
            role_arn=account.role_arn,
            external_id=account.external_id,
        )
    except ProviderValidationError as exc:
        account.status = CloudAccount.Status.INVALID
        account.last_validated_at = timezone.now()
        account.last_error = str(exc)[:255]
        account.save(update_fields=["status", "last_validated_at", "last_error", "updated_at"])
        record_audit(request.user, "onboarding.cloud_account.validate_failure", account)
        return Response(
            {"status": account.status, "error": account.last_error},
            status=status.HTTP_400_BAD_REQUEST,
        )
    account.status = CloudAccount.Status.VALID
    account.last_validated_at = timezone.now()
    account.last_error = ""
    account.metadata = {"identity_arn": result.arn, **result.metadata}
    account.save(
        update_fields=["status", "last_validated_at", "last_error", "metadata", "updated_at"]
    )
    profile = _profile(request.user)
    profile.current_step = OnboardingProfile.Step.SYNC
    profile.save(update_fields=["current_step", "updated_at"])
    record_audit(request.user, "onboarding.cloud_account.validate_success", account)
    return Response({"id": account.id, "status": account.status, "next_step": profile.current_step})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initial_sync(request, pk: int):
    organization = _organization_for_user(request.user)
    try:
        account = CloudAccount.objects.get(pk=pk, organization=organization)
    except CloudAccount.DoesNotExist:
        return Response({"detail": "Cloud account not found."}, status=status.HTTP_404_NOT_FOUND)
    if account.status != CloudAccount.Status.VALID:
        return Response(
            {"detail": "Validate the cloud account before the initial sync."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    inventory_sync = sync_inventory(account)
    today = timezone.localdate()
    month_start = today.replace(day=1)
    cost_sync = sync_costs(account, start_date=month_start, end_date=today + timedelta(days=1))
    inventory_ok = inventory_sync.status in {
        InventorySync.Status.SUCCESS,
        InventorySync.Status.PARTIAL,
    }
    costs_ok = cost_sync.status in {CostSync.Status.SUCCESS, CostSync.Status.PARTIAL}
    profile = _profile(request.user)
    if inventory_ok and costs_ok:
        _refresh_profile(profile)
    record_audit(
        request.user,
        "onboarding.initial_sync",
        account,
        {
            "inventory_status": inventory_sync.status,
            "cost_status": cost_sync.status,
            "inventory_sync_id": inventory_sync.id,
            "cost_sync_id": cost_sync.id,
        },
    )
    response_status = status.HTTP_200_OK if inventory_ok and costs_ok else status.HTTP_207_MULTI_STATUS
    return Response(
        {
            "inventory": {
                "status": inventory_sync.status,
                "discovered_count": inventory_sync.discovered_count,
                "errors": inventory_sync.errors,
            },
            "costs": {
                "status": cost_sync.status,
                "record_count": cost_sync.record_count,
                "errors": cost_sync.errors,
            },
            "next_step": profile.current_step,
        },
        status=response_status,
    )
