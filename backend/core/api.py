from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .audit import record_audit
from .models import AuditEvent, CloudAccount, Organization, OrganizationNode, Project
from .providers import ProviderValidationError, get_provider
from .rbac import GovernancePermission, PlatformAdminPermission
from .serializers import (
    AuditEventSerializer,
    CloudAccountSerializer,
    OrganizationNodeSerializer,
    OrganizationSerializer,
    ProjectSerializer,
    UserRoleSerializer,
)


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
    queryset = Organization.objects.all().order_by("name")
    serializer_class = OrganizationSerializer


class OrganizationNodeViewSet(AuditedModelViewSet):
    queryset = (
        OrganizationNode.objects.select_related("organization", "parent")
        .all()
        .order_by("organization__name", "name")
    )
    serializer_class = OrganizationNodeSerializer


class ProjectViewSet(AuditedModelViewSet):
    queryset = (
        Project.objects.select_related("organization", "node")
        .all()
        .order_by("organization__name", "name")
    )
    serializer_class = ProjectSerializer


class CloudAccountViewSet(AuditedModelViewSet):
    queryset = (
        CloudAccount.objects.select_related("organization", "project")
        .all()
        .order_by("provider", "name")
    )
    serializer_class = CloudAccountSerializer

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


class AuditEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditEvent.objects.select_related("actor").all()
    serializer_class = AuditEventSerializer
    permission_classes = [GovernancePermission]


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
