from datetime import date

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .reporting import build_cost_detail_report, build_resource_inventory_report, report_catalog


def _optional_bool(value):
    if value is None or value == "":
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    return None


def _optional_date(value, field):
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValidationError({field: "Use YYYY-MM-DD."}) from exc


def _csv_response(request, result, filename):
    organization = user_organization(request.user)
    if organization is not None:
        record_audit(
            request.user,
            "report.export",
            organization,
            {
                "report": result["report"].code,
                "format": "csv",
                "row_count": result["row_count"],
                "truncated": result["truncated"],
            },
        )
    response = HttpResponse(result["content"], content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Finopser-Report"] = result["report"].code
    response["X-Finopser-Row-Count"] = str(result["row_count"])
    response["X-Finopser-Truncated"] = "true" if result["truncated"] else "false"
    response["X-Finopser-Generated-At"] = result["generated_at"].isoformat()
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalog(request):
    return Response({"reports": report_catalog()})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resource_inventory_csv(request):
    result = build_resource_inventory_report(
        request.user,
        account_id=request.query_params.get("account"),
        resource_type=request.query_params.get("resource_type"),
        active=_optional_bool(request.query_params.get("active")),
    )
    return _csv_response(request, result, "finopser-resource-inventory.csv")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cost_detail_csv(request):
    start_date = _optional_date(request.query_params.get("start_date"), "start_date")
    end_date = _optional_date(request.query_params.get("end_date"), "end_date")
    if start_date and end_date and start_date > end_date:
        raise ValidationError({"end_date": "Must be on or after start_date."})
    result = build_cost_detail_report(
        request.user,
        account_id=request.query_params.get("account"),
        project_id=request.query_params.get("project"),
        service=request.query_params.get("service"),
        start_date=start_date,
        end_date=end_date,
    )
    return _csv_response(request, result, "finopser-cost-detail.csv")
