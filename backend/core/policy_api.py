from django.db.models import Count, Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import organization_scope_id, user_organization
from .models import AuditEvent, GovernancePolicy, PolicyRun, PolicyViolation
from .policies import BUILTIN_POLICY_CODES, evaluate_policies
from .rbac import CLOUD_ADMIN, PLATFORM_ADMIN, SECURITY_ENGINEER, user_has_role
from .tenant_scope import validate_related_organization


class PolicyWritePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(request.user, {PLATFORM_ADMIN, CLOUD_ADMIN, SECURITY_ENGINEER})


def _organization_id(user):
    return organization_scope_id(user)


def _policy_queryset(user):
    queryset = GovernancePolicy.objects.select_related(
        "organization", "node", "project", "cloud_account"
    )
    organization_id = _organization_id(user)
    if organization_id is None:
        return queryset
    return queryset.filter(
        Q(organization_id=organization_id)
        | Q(organization__isnull=True, code__in=BUILTIN_POLICY_CODES)
    ).distinct()


def _violation_queryset(user):
    queryset = PolicyViolation.objects.select_related("policy", "resource", "cloud_account")
    organization_id = _organization_id(user)
    if organization_id is not None:
        queryset = queryset.filter(cloud_account__organization_id=organization_id)
    return queryset


def _run_queryset(user):
    queryset = PolicyRun.objects.all()
    organization_id = _organization_id(user)
    if organization_id is None:
        return queryset
    run_ids = AuditEvent.objects.filter(
        action="policy.evaluate",
        metadata__organization_id=organization_id,
        object_type="PolicyRun",
    ).values_list("object_id", flat=True)
    return queryset.filter(id__in=run_ids)


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernancePolicy
        fields = [
            "id", "code", "name", "description", "severity", "mode", "enabled",
            "resource_type", "rule_key", "organization", "node", "project", "cloud_account",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        organization = attrs.get("organization", getattr(self.instance, "organization", None))
        node = attrs.get("node", getattr(self.instance, "node", None))
        project = attrs.get("project", getattr(self.instance, "project", None))
        account = attrs.get("cloud_account", getattr(self.instance, "cloud_account", None))
        if node and organization and node.organization_id != organization.id:
            raise serializers.ValidationError("Node must belong to the selected organization.")
        if project and organization and project.organization_id != organization.id:
            raise serializers.ValidationError("Project must belong to the selected organization.")
        if project and node and project.node_id != node.id:
            raise serializers.ValidationError("Project must belong to the selected organization node.")
        if account and organization and account.organization_id != organization.id:
            raise serializers.ValidationError("Cloud account must belong to the selected organization.")
        if account and project and account.project_id != project.id:
            raise serializers.ValidationError("Cloud account must belong to the selected project.")
        request = self.context.get("request")
        if request and not request.user.is_superuser and user_organization(request.user) is not None:
            validate_related_organization(request.user, organization, node, project, account)
        return attrs


class ViolationSerializer(serializers.ModelSerializer):
    policy_code = serializers.CharField(source="policy.code", read_only=True)
    policy_name = serializers.CharField(source="policy.name", read_only=True)
    policy_mode = serializers.CharField(source="policy.mode", read_only=True)
    resource_name = serializers.CharField(source="resource.name", read_only=True)
    resource_type = serializers.CharField(source="resource.resource_type", read_only=True)
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)

    class Meta:
        model = PolicyViolation
        fields = [
            "id", "policy", "policy_code", "policy_name", "policy_mode", "resource",
            "resource_name", "resource_type", "cloud_account", "account_name", "severity",
            "status", "evidence", "first_seen", "last_seen", "resolved_at",
        ]
        read_only_fields = fields


class PolicyRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyRun
        fields = [
            "id", "started_at", "completed_at", "passed_count", "violated_count",
            "unknown_count", "resolved_count",
        ]
        read_only_fields = fields


class PolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [PolicyWritePermission]
    serializer_class = PolicySerializer

    def get_queryset(self):
        return _policy_queryset(self.request.user)

    def perform_create(self, serializer):
        organization = user_organization(self.request.user)
        if not self.request.user.is_superuser and organization is not None:
            policy = serializer.save(created_by=self.request.user, organization=organization)
        else:
            policy = serializer.save(created_by=self.request.user)
        record_audit(self.request.user, "policy.create", policy)

    def perform_update(self, serializer):
        organization = user_organization(self.request.user)
        if not self.request.user.is_superuser and organization is not None:
            policy = serializer.save(organization=organization)
        else:
            policy = serializer.save()
        record_audit(self.request.user, "policy.update", policy)

    def perform_destroy(self, instance):
        if instance.organization_id is None and instance.code in BUILTIN_POLICY_CODES:
            raise PermissionDenied("Built-in policies cannot be deleted from a workspace.")
        record_audit(self.request.user, "policy.delete", instance)
        instance.delete()


class ViolationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PolicyWritePermission]
    serializer_class = ViolationSerializer

    def get_queryset(self):
        queryset = _violation_queryset(self.request.user)
        for field in ("status", "severity", "cloud_account", "policy"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class PolicyRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PolicyWritePermission]
    serializer_class = PolicyRunSerializer

    def get_queryset(self):
        return _run_queryset(self.request.user)


@api_view(["POST"])
@permission_classes([PolicyWritePermission])
def evaluate(request):
    if _organization_id(request.user) == -1:
        raise PermissionDenied("Complete organization setup before evaluating policies.")
    run = evaluate_policies(request.user)
    return Response(PolicyRunSerializer(run).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([PolicyWritePermission])
def summary(request):
    policies = _policy_queryset(request.user)
    violations = _violation_queryset(request.user)
    latest_run = _run_queryset(request.user).first()
    active = violations.filter(status=PolicyViolation.Status.OPEN)
    return Response({
        "policies": {
            "total": policies.count(),
            "enabled": policies.filter(enabled=True).count(),
            "observe": policies.filter(enabled=True, mode=GovernancePolicy.Mode.OBSERVE).count(),
            "recommend": policies.filter(enabled=True, mode=GovernancePolicy.Mode.RECOMMEND).count(),
        },
        "violations": {
            "open": active.count(),
            "resolved": violations.filter(status=PolicyViolation.Status.RESOLVED).count(),
            "by_severity": list(
                active.values("severity").annotate(count=Count("id")).order_by("severity")
            ),
        },
        "latest_run": PolicyRunSerializer(latest_run).data if latest_run else None,
    })
