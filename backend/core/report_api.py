from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .reporting import build_resource_inventory_report, report_catalog


def _optional_bool(value):
    if value is None or value == "":
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    return None


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
    response["Content-Disposition"] = 'attachment; filename="finopser-resource-inventory.csv"'
    response["X-Finopser-Report"] = result["report"].code
    response["X-Finopser-Row-Count"] = str(result["row_count"])
    response["X-Finopser-Truncated"] = "true" if result["truncated"] else "false"
    response["X-Finopser-Generated-At"] = result["generated_at"].isoformat()
    return response
