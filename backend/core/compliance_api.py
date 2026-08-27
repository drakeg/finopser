from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from .audit import record_audit
from .compliance import ensure_baseline_controls, evaluate_compliance
from .models import (
    ComplianceControl,
    ComplianceException,
    ComplianceFinding,
    ComplianceFramework,
    ComplianceRun,
)
from .rbac import CLOUD_ADMIN, PLATFORM_ADMIN, SECURITY_ENGINEER, user_has_role

class ComplianceWritePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(
            request.user,
            {PLATFORM_ADMIN, CLOUD_ADMIN, SECURITY_ENGINEER},
        )


class FrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceFramework
        fields = ["id", "code", "name", "version", "description", "enabled"]
        read_only_fields = fields


class ControlSerializer(serializers.ModelSerializer):
    framework_code = serializers.CharField(source="framework.code", read_only=True)

    class Meta:
        model = ComplianceControl
        fields = [
            "id",
            "framework",
            "framework_code",
            "code",
            "title",
            "description",
            "severity",
            "resource_type",
            "check_key",
        ]
        read_only_fields = fields


class FindingSerializer(serializers.ModelSerializer):
    control_code = serializers.CharField(source="control.code", read_only=True)
    control_title = serializers.CharField(source="control.title", read_only=True)
    resource_name = serializers.CharField(source="resource.name", read_only=True)
    resource_type = serializers.CharField(source="resource.resource_type", read_only=True)
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)

    class Meta:
        model = ComplianceFinding
        fields = [
            "id",
            "control",
            "control_code",
            "control_title",
            "resource",
            "resource_name",
            "resource_type",
            "cloud_account",
            "account_name",
            "severity",
            "status",
            "evidence",
            "first_seen",
            "last_seen",
            "resolved_at",
        ]
        read_only_fields = fields


class ExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceException
        fields = [
            "id",
            "control",
            "cloud_account",
            "resource",
            "reason",
            "expires_at",
            "is_active",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]

    def validate(self, attrs):
        resource = attrs.get("resource", getattr(self.instance, "resource", None))
        account = attrs.get("cloud_account", getattr(self.instance, "cloud_account", None))
        if resource and account and resource.cloud_account_id != account.id:
            raise serializers.ValidationError("Resource must belong to the selected cloud account.")
        return attrs


class RunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceRun
        fields = [
            "id",
            "started_at",
            "completed_at",
            "passed_count",
            "failed_count",
            "unknown_count",
            "resolved_count",
        ]
        read_only_fields = fields


class FrameworkViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ComplianceWritePermission]
    serializer_class = FrameworkSerializer
    queryset = ComplianceFramework.objects.all().order_by("code")


class ControlViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ComplianceWritePermission]
    serializer_class = ControlSerializer
    queryset = ComplianceControl.objects.select_related("framework").all()


class FindingViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ComplianceWritePermission]
    serializer_class = FindingSerializer

    def get_queryset(self):
        queryset = ComplianceFinding.objects.select_related(
            "control",
            "resource",
            "cloud_account",
        )
        for field in ("status", "severity", "cloud_account", "control"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class ExceptionViewSet(viewsets.ModelViewSet):
    permission_classes = [ComplianceWritePermission]
    serializer_class = ExceptionSerializer
    queryset = ComplianceException.objects.select_related("control", "cloud_account", "resource")

    def perform_create(self, serializer):
        exception = serializer.save(created_by=self.request.user)
        record_audit(self.request.user, "compliance.exception.create", exception)

    def perform_update(self, serializer):
        exception = serializer.save()
        record_audit(self.request.user, "compliance.exception.update", exception)

    def perform_destroy(self, instance):
        record_audit(self.request.user, "compliance.exception.delete", instance)
        instance.delete()


class RunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ComplianceWritePermission]
    serializer_class = RunSerializer
    queryset = ComplianceRun.objects.all()


@api_view(["POST"])
@permission_classes([ComplianceWritePermission])
def evaluate(request):
    run = evaluate_compliance(request.user)
    return Response(RunSerializer(run).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([ComplianceWritePermission])
def summary(request):
    ensure_baseline_controls()
    now = timezone.now()
    active_findings = ComplianceFinding.objects.exclude(status=ComplianceFinding.Status.RESOLVED)
    active_exceptions = ComplianceException.objects.filter(is_active=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    latest_run = ComplianceRun.objects.first()
    return Response(
        {
            "frameworks": ComplianceFramework.objects.filter(enabled=True).count(),
            "controls": ComplianceControl.objects.count(),
            "findings": {
                "open": ComplianceFinding.objects.filter(status=ComplianceFinding.Status.OPEN).count(),
                "excepted": ComplianceFinding.objects.filter(status=ComplianceFinding.Status.EXCEPTED).count(),
                "resolved": ComplianceFinding.objects.filter(status=ComplianceFinding.Status.RESOLVED).count(),
                "by_severity": list(
                    active_findings.values("severity")
                    .annotate(count=Count("id"))
                    .order_by("severity")
                ),
            },
            "active_exceptions": active_exceptions.count(),
            "latest_run": RunSerializer(latest_run).data if latest_run else None,
        }
    )
