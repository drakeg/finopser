# ruff: noqa: I001
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .models import OrganizationNode, Project
from .rbac import MANAGER_ROLES, user_has_role
from .vending_models import AccountVendingRequest


BASELINE_PROFILES = {
    "standard": ["organization-placement", "cost-allocation-tags", "baseline-logging"],
    "sandbox": ["organization-placement", "cost-allocation-tags", "sandbox-guardrails"],
    "production": ["organization-placement", "cost-allocation-tags", "baseline-logging", "production-guardrails"],
}


def _payload(item: AccountVendingRequest) -> dict:
    return {
        "id": item.id,
        "account_name": item.account_name,
        "account_email": item.account_email,
        "environment": item.environment,
        "purpose": item.purpose,
        "baseline_profile": item.baseline_profile,
        "status": item.status,
        "organization_node": item.organization_node_id,
        "project": item.project_id,
        "requested_by": item.requested_by.get_username(),
        "approved_by": item.approved_by.get_username() if item.approved_by else None,
        "rejection_reason": item.rejection_reason,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _scoped_item(request, pk: int):
    organization = user_organization(request.user)
    if organization is None:
        return None
    return AccountVendingRequest.objects.select_related("requested_by", "approved_by").filter(
        organization=organization,
        pk=pk,
    ).first()


def _related_object(model, organization, value):
    if value in (None, ""):
        return None
    return model.objects.filter(organization=organization, pk=value).first()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def requests(request):
    organization = user_organization(request.user)
    if organization is None:
        return Response({"detail": "Complete organization setup first."}, status=400)

    if request.method == "GET":
        items = AccountVendingRequest.objects.select_related("requested_by", "approved_by").filter(
            organization=organization
        )
        return Response([_payload(item) for item in items])

    account_name = str(request.data.get("account_name", "")).strip()
    account_email = str(request.data.get("account_email", "")).strip().lower()
    environment = str(request.data.get("environment", "")).strip().lower()
    baseline_profile = str(request.data.get("baseline_profile", "standard")).strip().lower()
    purpose = str(request.data.get("purpose", "")).strip()
    if not account_name or "@" not in account_email:
        return Response({"detail": "Account name and a valid account email are required."}, status=400)
    if environment not in AccountVendingRequest.Environment.values:
        return Response({"detail": "Choose a supported environment."}, status=400)
    if baseline_profile not in BASELINE_PROFILES:
        return Response({"detail": "Choose a supported baseline profile."}, status=400)

    node_value = request.data.get("organization_node")
    project_value = request.data.get("project")
    node = _related_object(OrganizationNode, organization, node_value)
    project = _related_object(Project, organization, project_value)
    if node_value not in (None, "") and node is None:
        return Response({"detail": "Organization node is outside this workspace or does not exist."}, status=400)
    if project_value not in (None, "") and project is None:
        return Response({"detail": "Project is outside this workspace or does not exist."}, status=400)

    try:
        with transaction.atomic():
            item = AccountVendingRequest.objects.create(
                organization=organization,
                organization_node=node,
                project=project,
                account_name=account_name,
                account_email=account_email,
                environment=environment,
                purpose=purpose,
                baseline_profile=baseline_profile,
                status=AccountVendingRequest.Status.PENDING_APPROVAL,
                requested_by=request.user,
            )
            record_audit(request.user, "account_vending.request", item, {"environment": environment, "baseline_profile": baseline_profile})
    except IntegrityError:
        return Response({"detail": "That account email already has a request in this workspace."}, status=status.HTTP_409_CONFLICT)
    return Response(_payload(item), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve(request, pk: int):
    if not user_has_role(request.user, MANAGER_ROLES):
        return Response({"detail": "Manager access is required."}, status=403)
    item = _scoped_item(request, pk)
    if item is None:
        return Response({"detail": "Request not found."}, status=404)
    if item.status != AccountVendingRequest.Status.PENDING_APPROVAL:
        return Response({"detail": "Only pending requests can be approved."}, status=409)
    item.status = AccountVendingRequest.Status.APPROVED
    item.approved_by = request.user
    item.rejection_reason = ""
    item.save(update_fields=["status", "approved_by", "rejection_reason", "updated_at"])
    record_audit(request.user, "account_vending.approve", item, {})
    return Response(_payload(item))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject(request, pk: int):
    if not user_has_role(request.user, MANAGER_ROLES):
        return Response({"detail": "Manager access is required."}, status=403)
    item = _scoped_item(request, pk)
    if item is None:
        return Response({"detail": "Request not found."}, status=404)
    if item.status != AccountVendingRequest.Status.PENDING_APPROVAL:
        return Response({"detail": "Only pending requests can be rejected."}, status=409)
    reason = str(request.data.get("reason", "")).strip()
    if not reason:
        return Response({"detail": "A rejection reason is required."}, status=400)
    item.status = AccountVendingRequest.Status.REJECTED
    item.approved_by = None
    item.rejection_reason = reason
    item.save(update_fields=["status", "approved_by", "rejection_reason", "updated_at"])
    record_audit(request.user, "account_vending.reject", item, {"reason": reason})
    return Response(_payload(item))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview(request, pk: int):
    item = _scoped_item(request, pk)
    if item is None:
        return Response({"detail": "Request not found."}, status=404)
    actions = BASELINE_PROFILES[item.baseline_profile]
    result = {
        "request": _payload(item),
        "provider": "disabled",
        "live_provisioning": False,
        "ready_for_provisioning": item.status == AccountVendingRequest.Status.APPROVED,
        "intended_actions": actions,
        "placement": {
            "organization_node": item.organization_node_id,
            "project": item.project_id,
        },
    }
    record_audit(request.user, "account_vending.preview", item, {"ready_for_provisioning": result["ready_for_provisioning"]})
    return Response(result)
