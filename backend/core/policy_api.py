from django.db.models import Count
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from .audit import record_audit
from .models import GovernancePolicy, PolicyRun, PolicyViolation
from .policies import evaluate_policies
from .rbac import CLOUD_ADMIN, PLATFORM_ADMIN, SECURITY_ENGINEER, user_has_role


class PolicyWritePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(request.user, {PLATFORM_ADMIN, CLOUD_ADMIN, SECURITY_ENGINEER})


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
        fields = ["id", "started_at", "completed_at", "passed_count", "violated_count", "unknown_count", "resolved_count"]
        read_only_fields = fields


class PolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [PolicyWritePermission]
    serializer_class = PolicySerializer
    queryset = GovernancePolicy.objects.select_related("organization", "node", "project", "cloud_account")

    def perform_create(self, serializer):
        policy = serializer.save(created_by=self.request.user)
        record_audit(self.request.user, "policy.create", policy)

    def perform_update(self, serializer):
        policy = serializer.save()
        record_audit(self.request.user, "policy.update", policy)

    def perform_destroy(self, instance):
        record_audit(self.request.user, "policy.delete", instance)
        instance.delete()


class ViolationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PolicyWritePermission]
    serializer_class = ViolationSerializer

    def get_queryset(self):
        queryset = PolicyViolation.objects.select_related("policy", "resource", "cloud_account")
        for field in ("status", "severity", "cloud_account", "policy"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class PolicyRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PolicyWritePermission]
    serializer_class = PolicyRunSerializer
    queryset = PolicyRun.objects.all()


@api_view(["POST"])
@permission_classes([PolicyWritePermission])
def evaluate(request):
    run = evaluate_policies(request.user)
    return Response(PolicyRunSerializer(run).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([PolicyWritePermission])
def summary(request):
    latest_run = PolicyRun.objects.first()
    active = PolicyViolation.objects.filter(status=PolicyViolation.Status.OPEN)
    return Response({
        "policies": {
            "total": GovernancePolicy.objects.count(),
            "enabled": GovernancePolicy.objects.filter(enabled=True).count(),
            "observe": GovernancePolicy.objects.filter(enabled=True, mode=GovernancePolicy.Mode.OBSERVE).count(),
            "recommend": GovernancePolicy.objects.filter(enabled=True, mode=GovernancePolicy.Mode.RECOMMEND).count(),
        },
        "violations": {
            "open": active.count(),
            "resolved": PolicyViolation.objects.filter(status=PolicyViolation.Status.RESOLVED).count(),
            "by_severity": list(active.values("severity").annotate(count=Count("id")).order_by("severity")),
        },
        "latest_run": PolicyRunSerializer(latest_run).data if latest_run else None,
    })
