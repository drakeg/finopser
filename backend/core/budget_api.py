from decimal import Decimal

from django.db.models import Count
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from .audit import record_audit
from .budgets import budget_snapshot, evaluate_budgets
from .entitlements import organization_scope_id, user_organization
from .models import Budget, BudgetAlert
from .rbac import CLOUD_ADMIN, FINOPS_ANALYST, PLATFORM_ADMIN, user_has_role
from .tenant_scope import validate_related_organization


class BudgetWritePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(request.user, {PLATFORM_ADMIN, CLOUD_ADMIN, FINOPS_ANALYST})


class BudgetSerializer(serializers.ModelSerializer):
    snapshot = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id", "name", "amount", "currency", "warning_threshold", "critical_threshold",
            "enabled", "organization", "node", "project", "cloud_account", "created_by",
            "created_at", "updated_at", "snapshot",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at", "snapshot"]

    def get_snapshot(self, obj):
        return budget_snapshot(obj)

    def validate(self, attrs):
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        warning = attrs.get("warning_threshold", getattr(self.instance, "warning_threshold", Decimal("80")))
        critical = attrs.get("critical_threshold", getattr(self.instance, "critical_threshold", Decimal("90")))
        if amount is None or amount <= 0:
            raise serializers.ValidationError("Budget amount must be greater than zero.")
        if warning <= 0 or critical >= 100 or warning >= critical:
            raise serializers.ValidationError("Thresholds must satisfy 0 < warning < critical < 100.")

        organization = attrs.get("organization", getattr(self.instance, "organization", None))
        node = attrs.get("node", getattr(self.instance, "node", None))
        project = attrs.get("project", getattr(self.instance, "project", None))
        account = attrs.get("cloud_account", getattr(self.instance, "cloud_account", None))
        if node and organization and node.organization_id != organization.id:
            raise serializers.ValidationError("Node must belong to the selected organization.")
        if project and organization and project.organization_id != organization.id:
            raise serializers.ValidationError("Project must belong to the selected organization.")
        if project and node and project.node_id != node.id:
            raise serializers.ValidationError("Project must belong to the selected node.")
        if account and organization and account.organization_id != organization.id:
            raise serializers.ValidationError("Cloud account must belong to the selected organization.")
        if account and project and account.project_id != project.id:
            raise serializers.ValidationError("Cloud account must belong to the selected project.")
        request = self.context.get("request")
        if request:
            validate_related_organization(request.user, organization, node, project, account)
        return attrs


class BudgetAlertSerializer(serializers.ModelSerializer):
    budget_name = serializers.CharField(source="budget.name", read_only=True)

    class Meta:
        model = BudgetAlert
        fields = ["id", "budget", "budget_name", "period", "level", "status", "actual_amount", "utilization", "first_seen", "last_seen", "resolved_at"]
        read_only_fields = fields


class BudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [BudgetWritePermission]
    serializer_class = BudgetSerializer

    def get_queryset(self):
        queryset = Budget.objects.select_related("organization", "node", "project", "cloud_account", "created_by")
        organization_id = organization_scope_id(self.request.user)
        return queryset if organization_id is None else queryset.filter(organization_id=organization_id)

    def perform_create(self, serializer):
        organization = user_organization(self.request.user)
        if organization is not None:
            budget = serializer.save(created_by=self.request.user, organization=organization)
        else:
            budget = serializer.save(created_by=self.request.user)
        record_audit(self.request.user, "budget.create", budget)

    def perform_update(self, serializer):
        budget = serializer.save()
        record_audit(self.request.user, "budget.update", budget)

    def perform_destroy(self, instance):
        record_audit(self.request.user, "budget.delete", instance)
        instance.delete()


class BudgetAlertViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [BudgetWritePermission]
    serializer_class = BudgetAlertSerializer

    def get_queryset(self):
        queryset = BudgetAlert.objects.select_related("budget")
        organization_id = organization_scope_id(self.request.user)
        if organization_id is not None:
            queryset = queryset.filter(budget__organization_id=organization_id)
        for field in ("status", "level", "budget", "period"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


@api_view(["POST"])
@permission_classes([BudgetWritePermission])
def evaluate(request):
    snapshots = evaluate_budgets(request.user)
    return Response({"evaluated": len(snapshots), "budgets": [{"id": budget.id, "name": budget.name, **snapshot} for budget, snapshot in snapshots]}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([BudgetWritePermission])
def summary(request):
    budgets = Budget.objects.filter(enabled=True).order_by("name", "id")
    organization_id = organization_scope_id(request.user)
    if organization_id is not None:
        budgets = budgets.filter(organization_id=organization_id)
    snapshots = [budget_snapshot(budget) for budget in budgets]
    total_budget = sum((budget.amount for budget in budgets), Decimal("0"))
    total_actual = sum((snapshot["actual"] for snapshot in snapshots), Decimal("0"))
    open_alerts = BudgetAlert.objects.filter(status=BudgetAlert.Status.OPEN, budget__in=budgets)
    return Response({
        "budgets": {"total": budgets.count(), "enabled": budgets.count(), "amount": total_budget, "actual": total_actual},
        "status": {
            "ok": sum(snapshot["level"] == "ok" for snapshot in snapshots),
            "warning": sum(snapshot["level"] == BudgetAlert.Level.WARNING for snapshot in snapshots),
            "critical": sum(snapshot["level"] == BudgetAlert.Level.CRITICAL for snapshot in snapshots),
            "exceeded": sum(snapshot["level"] == BudgetAlert.Level.EXCEEDED for snapshot in snapshots),
            "no_data": sum(not snapshot["has_data"] for snapshot in snapshots),
        },
        "alerts": {"open": open_alerts.count(), "by_level": list(open_alerts.values("level").annotate(count=Count("id")).order_by("level"))},
        "items": [{"id": budget.id, "name": budget.name, "amount": budget.amount, **snapshot} for budget, snapshot in zip(budgets, snapshots, strict=True)],
    })
