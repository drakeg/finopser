import csv
from datetime import date

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .audit import record_audit
from .costs import sync_costs
from .entitlements import user_organization
from .models import CloudAccount, CostRecord, CostSync
from .rbac import GovernancePermission


class CostRecordSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = CostRecord
        fields = [
            "id",
            "provider",
            "cloud_account",
            "account_name",
            "project",
            "project_name",
            "provider_account_id",
            "usage_date",
            "service",
            "region",
            "amount",
            "currency",
        ]
        read_only_fields = fields


class CostSyncSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="cloud_account.name", read_only=True)

    class Meta:
        model = CostSync
        fields = [
            "id",
            "cloud_account",
            "account_name",
            "start_date",
            "end_date",
            "status",
            "started_at",
            "completed_at",
            "record_count",
            "errors",
        ]
        read_only_fields = fields


def _parse_date(value: str, field: str):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({field: "Use YYYY-MM-DD."}) from exc


def _total(queryset):
    return queryset.aggregate(total=Sum("amount"))["total"] or 0


def _organization_id(user):
    if user.is_superuser:
        return None
    organization = user_organization(user)
    return organization.id if organization else -1


@api_view(["POST"])
@permission_classes([GovernancePermission])
def sync_account_costs(request, pk: int):
    queryset = CloudAccount.objects.all()
    organization_id = _organization_id(request.user)
    if organization_id is not None:
        queryset = queryset.filter(organization_id=organization_id)
    try:
        account = queryset.get(pk=pk)
    except CloudAccount.DoesNotExist:
        return Response({"error": "Cloud account not found."}, status=status.HTTP_404_NOT_FOUND)
    if account.status != CloudAccount.Status.VALID:
        return Response(
            {"error": "Cloud account must be validated before cost sync."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_date = _parse_date(request.data.get("start_date"), "start_date")
        end_date = _parse_date(request.data.get("end_date"), "end_date")
    except serializers.ValidationError as exc:
        return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
    if end_date <= start_date:
        return Response(
            {"end_date": "End date must be later than start date. AWS Cost Explorer end dates are exclusive."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if (end_date - start_date).days > 366:
        return Response(
            {"end_date": "A single sync may cover at most 366 days."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    record_audit(
        request.user,
        "cost_sync_requested",
        account,
        {"start": str(start_date), "end": str(end_date)},
    )
    sync = sync_costs(account, start_date=start_date, end_date=end_date)
    record_audit(
        request.user,
        f"cost_sync_{sync.status}",
        account,
        {"sync_id": sync.id, "record_count": sync.record_count, "errors": len(sync.errors)},
    )
    response_status = (
        status.HTTP_200_OK
        if sync.status in {CostSync.Status.SUCCESS, CostSync.Status.PARTIAL}
        else status.HTTP_400_BAD_REQUEST
    )
    return Response(CostSyncSerializer(sync).data, status=response_status)


class CostRecordViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CostRecordSerializer
    permission_classes = [GovernancePermission]

    def get_queryset(self):
        queryset = CostRecord.objects.select_related("cloud_account", "project").all()
        organization_id = _organization_id(self.request.user)
        if organization_id is not None:
            queryset = queryset.filter(cloud_account__organization_id=organization_id)
        exact_filters = {
            "cloud_account_id": self.request.query_params.get("cloud_account"),
            "service": self.request.query_params.get("service"),
            "region": self.request.query_params.get("region"),
            "project_id": self.request.query_params.get("project"),
            "currency": self.request.query_params.get("currency"),
        }
        for field, value in exact_filters.items():
            if value:
                queryset = queryset.filter(**{field: value})
        start = self.request.query_params.get("start_date")
        end = self.request.query_params.get("end_date")
        if start:
            queryset = queryset.filter(usage_date__gte=start)
        if end:
            queryset = queryset.filter(usage_date__lt=end)
        return queryset

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self.get_queryset()
        today = timezone.localdate()
        month_start = today.replace(day=1)
        return Response(
            {
                "total": _total(queryset),
                "mtd": _total(
                    queryset.filter(usage_date__gte=month_start, usage_date__lte=today)
                ),
                "by_service": list(
                    queryset.values("service")
                    .annotate(total=Sum("amount"))
                    .order_by("-total", "service")
                ),
                "by_account": list(
                    queryset.values("cloud_account", "cloud_account__name")
                    .annotate(total=Sum("amount"))
                    .order_by("-total")
                ),
                "by_region": list(
                    queryset.values("region")
                    .annotate(total=Sum("amount"))
                    .order_by("-total", "region")
                ),
                "by_project": list(
                    queryset.values("project", "project__name")
                    .annotate(total=Sum("amount"))
                    .order_by("-total")
                ),
                "monthly": list(
                    queryset.annotate(month=TruncMonth("usage_date"))
                    .values("month")
                    .annotate(total=Sum("amount"))
                    .order_by("month")
                ),
            }
        )

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="finopser-costs.csv"'
        writer = csv.writer(response)
        writer.writerow(["date", "account", "project", "service", "region", "amount", "currency"])
        for record in self.get_queryset().iterator():
            writer.writerow(
                [
                    record.usage_date,
                    record.cloud_account.name,
                    record.project.name if record.project else "",
                    record.service,
                    record.region,
                    record.amount,
                    record.currency,
                ]
            )
        return response


class CostSyncViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CostSyncSerializer
    permission_classes = [GovernancePermission]

    def get_queryset(self):
        queryset = CostSync.objects.select_related("cloud_account").all()
        organization_id = _organization_id(self.request.user)
        if organization_id is not None:
            queryset = queryset.filter(cloud_account__organization_id=organization_id)
        account = self.request.query_params.get("cloud_account")
        return queryset.filter(cloud_account_id=account) if account else queryset
