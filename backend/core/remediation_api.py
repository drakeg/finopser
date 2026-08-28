from django.db.models import Count
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from .audit import record_audit
from .automation_models import RemediationAction, RemediationEvent
from .rbac import (
    CLOUD_ADMIN,
    FINOPS_ANALYST,
    PLATFORM_ADMIN,
    SECURITY_ENGINEER,
    user_has_role,
)
from .remediation import (
    ACTION_REGISTRY,
    RemediationError,
    StaleEvidenceError,
    approve_action,
    execute_action,
    preview_action,
    reject_action,
)

REQUEST_ROLES = {PLATFORM_ADMIN, CLOUD_ADMIN, FINOPS_ANALYST, SECURITY_ENGINEER}
EXECUTE_ROLES = {PLATFORM_ADMIN, CLOUD_ADMIN}


class RemediationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(request.user, REQUEST_ROLES)


class RemediationEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = RemediationEvent
        fields = ["id", "event_type", "actor", "actor_name", "metadata", "created_at"]
        read_only_fields = fields


class RemediationActionSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source="resource.name", read_only=True)
    resource_type = serializers.CharField(source="resource.resource_type", read_only=True)
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.username", read_only=True)
    executed_by_name = serializers.CharField(source="executed_by.username", read_only=True)
    events = RemediationEventSerializer(many=True, read_only=True)

    class Meta:
        model = RemediationAction
        fields = [
            "id",
            "recommendation",
            "resource",
            "resource_name",
            "resource_type",
            "cloud_account",
            "account_name",
            "action_key",
            "status",
            "simulation",
            "parameters",
            "preview",
            "evidence_fingerprint",
            "provider_result",
            "error",
            "requested_by",
            "requested_by_name",
            "requested_at",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "executed_by",
            "executed_by_name",
            "executed_at",
            "updated_at",
            "events",
        ]
        read_only_fields = [
            "status",
            "preview",
            "evidence_fingerprint",
            "provider_result",
            "error",
            "requested_by",
            "requested_at",
            "approved_by",
            "approved_at",
            "executed_by",
            "executed_at",
            "updated_at",
            "events",
        ]

    def validate(self, attrs):
        resource = attrs.get("resource")
        account = attrs.get("cloud_account")
        recommendation = attrs.get("recommendation")
        if resource and account and resource.cloud_account_id != account.id:
            raise serializers.ValidationError("Resource must belong to the selected cloud account.")
        if recommendation and recommendation.resource_id and resource:
            if recommendation.resource_id != resource.id:
                raise serializers.ValidationError("Recommendation resource must match the remediation resource.")
        if attrs.get("action_key") not in ACTION_REGISTRY:
            raise serializers.ValidationError("Action is not allowlisted.")
        return attrs


class RemediationActionViewSet(viewsets.ModelViewSet):
    permission_classes = [RemediationPermission]
    serializer_class = RemediationActionSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = RemediationAction.objects.select_related(
            "recommendation",
            "resource",
            "cloud_account",
            "requested_by",
            "approved_by",
            "executed_by",
        ).prefetch_related("events")
        for field in ("status", "action_key", "simulation", "cloud_account", "resource"):
            value = self.request.query_params.get(field)
            if value is not None:
                queryset = queryset.filter(**{field: value})
        return queryset

    def perform_create(self, serializer):
        action_obj = serializer.save(requested_by=self.request.user)
        RemediationEvent.objects.create(
            action=action_obj,
            event_type="requested",
            actor=self.request.user,
            metadata={"simulation": action_obj.simulation},
        )
        record_audit(
            self.request.user,
            "remediation.request",
            action_obj,
            {"action_key": action_obj.action_key, "simulation": action_obj.simulation},
        )

    def _manager_required(self, request):
        if not user_has_role(request.user, EXECUTE_ROLES):
            return Response({"detail": "Platform or Cloud Administrator role required."}, status=403)
        return None

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        action_obj = self.get_object()
        try:
            preview_action(action_obj, request.user)
        except RemediationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(action_obj).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        denied = self._manager_required(request)
        if denied:
            return denied
        action_obj = self.get_object()
        try:
            approve_action(action_obj, request.user)
        except RemediationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(action_obj).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        denied = self._manager_required(request)
        if denied:
            return denied
        action_obj = self.get_object()
        try:
            reject_action(action_obj, request.user)
        except RemediationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(action_obj).data)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        denied = self._manager_required(request)
        if denied:
            return denied
        action_obj = self.get_object()
        try:
            execute_action(action_obj, request.user)
        except StaleEvidenceError as exc:
            return Response({"detail": str(exc), "status": "stale"}, status=status.HTTP_409_CONFLICT)
        except RemediationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(action_obj).data)


@api_view(["GET"])
@permission_classes([RemediationPermission])
def action_catalog(request):
    return Response(ACTION_REGISTRY)


@api_view(["GET"])
@permission_classes([RemediationPermission])
def summary(request):
    actions = RemediationAction.objects.all()
    return Response(
        {
            "total": actions.count(),
            "pending_approval": actions.filter(status=RemediationAction.Status.PREVIEWED).count(),
            "approved": actions.filter(status=RemediationAction.Status.APPROVED).count(),
            "succeeded": actions.filter(status=RemediationAction.Status.SUCCEEDED).count(),
            "failed": actions.filter(status=RemediationAction.Status.FAILED).count(),
            "stale": actions.filter(status=RemediationAction.Status.STALE).count(),
            "simulation": actions.filter(simulation=True).count(),
            "by_status": list(actions.values("status").annotate(count=Count("id")).order_by("status")),
            "catalog": ACTION_REGISTRY,
        }
    )
