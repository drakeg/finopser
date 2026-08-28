from django.db.models import Case, Count, DecimalField, Sum, Value, When
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from .audit import record_audit
from .rbac import (
    CLOUD_ADMIN,
    FINOPS_ANALYST,
    PLATFORM_ADMIN,
    SECURITY_ENGINEER,
    user_has_role,
)
from .recommendation_models import Recommendation, RecommendationRun
from .recommendations import generate_recommendations

RECOMMENDATION_ROLES = {PLATFORM_ADMIN, CLOUD_ADMIN, FINOPS_ANALYST, SECURITY_ENGINEER}


class RecommendationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user_has_role(request.user, RECOMMENDATION_ROLES)


class RecommendationSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    resource_name = serializers.CharField(source="resource.name", read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "source_type",
            "category",
            "priority",
            "status",
            "title",
            "detail",
            "action",
            "estimated_monthly_savings",
            "evidence",
            "cloud_account",
            "account_name",
            "project",
            "project_name",
            "resource",
            "resource_name",
            "first_seen",
            "last_seen",
            "resolved_at",
            "dismissed_at",
        ]
        read_only_fields = fields


class RecommendationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationRun
        fields = [
            "id",
            "started_at",
            "completed_at",
            "generated_count",
            "resolved_count",
            "open_count",
            "dismissed_count",
        ]
        read_only_fields = fields


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [RecommendationPermission]
    serializer_class = RecommendationSerializer

    def get_queryset(self):
        priority_order = Case(
            When(priority="critical", then=Value(0)),
            When(priority="high", then=Value(1)),
            When(priority="medium", then=Value(2)),
            default=Value(3),
        )
        queryset = Recommendation.objects.select_related(
            "cloud_account", "project", "resource"
        ).annotate(priority_rank=priority_order)
        for field in (
            "status",
            "category",
            "priority",
            "source_type",
            "cloud_account",
            "project",
        ):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset.order_by(
            "priority_rank",
            "-estimated_monthly_savings",
            "title",
        )

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        recommendation = self.get_object()
        recommendation.status = Recommendation.Status.DISMISSED
        recommendation.dismissed_at = timezone.now()
        recommendation.dismissed_by = request.user
        recommendation.resolved_at = None
        recommendation.save(
            update_fields=["status", "dismissed_at", "dismissed_by", "resolved_at"]
        )
        record_audit(request.user, "recommendation.dismiss", recommendation)
        return Response(self.get_serializer(recommendation).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        recommendation = self.get_object()
        recommendation.status = Recommendation.Status.OPEN
        recommendation.dismissed_at = None
        recommendation.dismissed_by = None
        recommendation.resolved_at = None
        recommendation.save(
            update_fields=["status", "dismissed_at", "dismissed_by", "resolved_at"]
        )
        record_audit(request.user, "recommendation.reopen", recommendation)
        return Response(self.get_serializer(recommendation).data)


class RecommendationRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [RecommendationPermission]
    serializer_class = RecommendationRunSerializer
    queryset = RecommendationRun.objects.all()


@api_view(["POST"])
@permission_classes([RecommendationPermission])
def generate(request):
    run = generate_recommendations(request.user)
    return Response(RecommendationRunSerializer(run).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([RecommendationPermission])
def summary(request):
    open_items = Recommendation.objects.filter(status=Recommendation.Status.OPEN)
    savings = open_items.aggregate(
        total=Sum("estimated_monthly_savings", output_field=DecimalField())
    )["total"]
    latest = RecommendationRun.objects.first()
    return Response(
        {
            "open": open_items.count(),
            "dismissed": Recommendation.objects.filter(
                status=Recommendation.Status.DISMISSED
            ).count(),
            "resolved": Recommendation.objects.filter(
                status=Recommendation.Status.RESOLVED
            ).count(),
            "estimated_monthly_savings": savings,
            "by_category": list(
                open_items.values("category")
                .annotate(count=Count("id"))
                .order_by("category")
            ),
            "by_priority": list(
                open_items.values("priority")
                .annotate(count=Count("id"))
                .order_by("priority")
            ),
            "latest_run": RecommendationRunSerializer(latest).data if latest else None,
        }
    )
