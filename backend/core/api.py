from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .inventory import sync_inventory
from .models import (
    AuditEvent,
    CloudAccount,
    CloudResource,
    InventorySync,
    Organization,
    OrganizationNode,
    Project,
)
from .providers import ProviderValidationError, get_provider
from .rbac import GovernancePermission, PlatformAdminPermission
from .serializers import (
    AuditEventSerializer,
    CloudAccountSerializer,
    CloudResourceSerializer,
    InventorySyncSerializer,
    OrganizationNodeSerializer,
    OrganizationSerializer,
    ProjectSerializer,
    UserRoleSerializer,
)


def _organization_id(request):
    if request.user.is_superuser:
        return None
    organization = user_organization(request.user)
    return organization.id if organization else -1


class AuditedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [GovernancePermission]

    def perform_create(self, serializer):
        obj = serializer.save()
        record_audit(self.request.user, "create", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        record_audit(self.request.user, "update", obj)

    def perform_destroy(self, instance):
        record_audit(self.request.user, "delete", instance)
        instance.delete()


class OrganizationViewSet(AuditedModelViewSet):
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        queryset = Organization.objects.all().order_by("name")
        organization_id = _organization_id(self.request)
        return queryset if organization_id is None else queryset.filter(id=organization_id)


class OrganizationNodeViewSet(AuditedModelViewSet):
    serializer_class = OrganizationNodeSerializer

    def get_queryset(self):
        queryset = OrganizationNode.objects.select_related("organization", "parent").order_by(
            "organization__name", "name"
        )
        organization_id = _organization_id(self.request)
        return queryset if organization_id is None else queryset.filter(organization_id=organization_id)


class ProjectViewSet(AuditedModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = Project.objects.select_related("organization", "node").order_by(
            "organization__name", "name"
        )
        organization_id = _organization_id(self.request)
        return queryset if organization_id is None else queryset.filter(organization_id=organization_id)


class CloudAccountViewSet(AuditedModelViewSet):
    serializer_class = CloudAccountSerializer

    def get_queryset(self):
        queryset = CloudAccount.objects.select_related("organization", "project").order_by(
            "provider", "name"
        )
        organization_id = _organization_id(self.request)
        return queryset if organization_id is None else queryset.filter(organization_id=organization_id)

    def perform_update(self, serializer):
        account = serializer.save(
            status=CloudAccount.Status.UNVALIDATED,
            last_validated_at=None,
            last_error="",
            metadata={},
        )
        record_audit(self.request.user, "update", account)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_connection(self, request, pk=None):
        account = self.get_object()
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
            record_audit(
                request.user,
                "validate_failure",
                account,
                {"provider": account.provider, "status": account.status},
            )
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
        record_audit(
            request.user,
            "validate_success",
            account,
            {"provider": account.provider, "provider_account_id": result.provider_account_id},
        )
        return Response(self.get_serializer(account).data)

    @action(detail=True, methods=["post"], url_path="sync-inventory")
    def sync_inventory_action(self, request, pk=None):
        account = self.get_object()
        if account.status != CloudAccount.Status.VALID:
            return Response(
                {"error": "Cloud account must be validated before inventory sync."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record_audit(request.user, "inventory_sync_requested", account)
        sync = sync_inventory(account)
        record_audit(
            request.user,
            f"inventory_sync_{sync.status}",
            account,
            {
                "sync_id": sync.id,
                "discovered_count": sync.discovered_count,
                "errors": len(sync.errors),
            },
        )
        response_status = (
            status.HTTP_200_OK
            if sync.status in {InventorySync.Status.SUCCESS, InventorySync.Status.PARTIAL}
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(InventorySyncSerializer(sync).data, status=response_status)


class CloudResourceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CloudResourceSerializer
    permission_classes = [GovernancePermission]

    def get_queryset(self):
        queryset = CloudResource.objects.select_related("cloud_account").all()
        organization_id = _organization_id(self.request)
        if organization_id is not None:
            queryset = queryset.filter(cloud_account__organization_id=organization_id)
        filters = {
            "cloud_account_id": self.request.query_params.get("cloud_account"),
            "resource_type": self.request.query_params.get("resource_type"),
            "region": self.request.query_params.get("region"),
            "state": self.request.query_params.get("state"),
        }
        for field, value in filters.items():
            if value:
                queryset = queryset.filter(**{field: value})
        active = self.request.query_params.get("active")
        if active in {"true", "false"}:
            queryset = queryset.filter(is_active=active == "true")
        return queryset

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self.get_queryset()
        active = queryset.filter(is_active=True)
        by_type = list(
            active.values("resource_type")
            .annotate(count=Count("id"))
            .order_by("-count", "resource_type")
        )
        return Response(
            {
                "total": queryset.count(),
                "active": active.count(),
                "inactive": queryset.filter(is_active=False).count(),
                "by_type": by_type,
            }
        )


class InventorySyncViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InventorySyncSerializer
    permission_classes = [GovernancePermission]

    def get_queryset(self):
        queryset = InventorySync.objects.select_related("cloud_account").all()
        organization_id = _organization_id(self.request)
        if organization_id is not None:
            queryset = queryset.filter(cloud_account__organization_id=organization_id)
        cloud_account = self.request.query_params.get("cloud_account")
        if cloud_account:
            queryset = queryset.filter(cloud_account_id=cloud_account)
        return queryset


class AuditEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [GovernancePermission]

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("actor").all()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(actor=self.request.user)


class UserRoleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.prefetch_related("groups").all().order_by("username")
    serializer_class = UserRoleSerializer
    permission_classes = [PlatformAdminPermission]

    @action(detail=True, methods=["put"], url_path="roles")
    def roles(self, request, pk=None):
        user = self.get_object()
        roles = request.data.get("roles", [])
        if not isinstance(roles, list):
            return Response(
                {"roles": "Expected a list of role names."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            user,
            data={},
            partial=True,
            context={"request": request, "requested_roles": roles},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit(request.user, "update_roles", user, {"roles": roles})
        return Response(self.get_serializer(user).data)
