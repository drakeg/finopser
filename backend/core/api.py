from django.contrib.auth.models import User
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .audit import record_audit
from .models import AuditEvent, Organization, OrganizationNode, Project
from .rbac import GovernancePermission, PlatformAdminPermission
from .serializers import (
    AuditEventSerializer,
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
