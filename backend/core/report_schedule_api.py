from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .audit import record_audit
from .entitlements import user_organization
from .rbac import MANAGER_ROLES, user_has_role
from .report_models import ReportGeneration, ReportSchedule
from .reporting import (
    REPORT_CATALOG,
    build_audit_events_report,
    build_compliance_findings_report,
    build_cost_detail_report,
    build_policy_violations_report,
    build_resource_inventory_report,
    report_allowed,
)
from .reporting_actions import (
    ACTION_REPORT_CATALOG,
    action_report_allowed,
    build_recommendations_report,
    build_remediation_history_report,
)


REPORT_BUILDERS = {
    "resource-inventory": build_resource_inventory_report,
    "cost-detail": build_cost_detail_report,
    "compliance-findings": build_compliance_findings_report,
    "policy-violations": build_policy_violations_report,
    "recommendations": build_recommendations_report,
    "remediation-history": build_remediation_history_report,
    "audit-events": build_audit_events_report,
}


def _organization_or_400(request):
    organization = user_organization(request.user)
    if organization is None:
        return None, Response({"detail": "Complete organization setup first."}, status=400)
    return organization, None


def _manager_or_403(request):
    if not user_has_role(request.user, MANAGER_ROLES):
        return Response({"detail": "Manager access is required."}, status=403)
    return None


def _report_supported(user, code):
    if code in REPORT_CATALOG:
        return report_allowed(user, code)
    if code in ACTION_REPORT_CATALOG:
        return action_report_allowed(user, code)
    return False


def _payload(schedule):
    return {
        "id": schedule.id,
        "name": schedule.name,
        "report_code": schedule.report_code,
        "cadence": schedule.cadence,
        "is_active": schedule.is_active,
        "created_by": schedule.created_by.get_username(),
        "created_at": schedule.created_at,
        "disabled_at": schedule.disabled_at,
    }


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def schedules(request):
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    if request.method == "GET":
        queryset = ReportSchedule.objects.select_related("created_by").filter(organization=organization)
        return Response([_payload(item) for item in queryset if _report_supported(request.user, item.report_code)])

    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    name = str(request.data.get("name", "")).strip()
    code = str(request.data.get("report_code", "")).strip()
    cadence = str(request.data.get("cadence", "")).strip()
    if not name or len(name) > 120:
        return Response({"detail": "A schedule name of 120 characters or fewer is required."}, status=400)
    if not _report_supported(request.user, code):
        return Response({"detail": "Unsupported or unavailable report."}, status=400)
    if cadence not in ReportSchedule.Cadence.values:
        return Response({"detail": "Unsupported report cadence."}, status=400)
    try:
        schedule = ReportSchedule.objects.create(
            organization=organization,
            name=name,
            report_code=code,
            cadence=cadence,
            created_by=request.user,
        )
    except IntegrityError:
        return Response({"detail": "A report schedule with that name already exists."}, status=status.HTTP_409_CONFLICT)
    record_audit(
        request.user,
        "report_schedule.create",
        schedule,
        {"report": code, "cadence": cadence},
    )
    return Response(_payload(schedule), status=status.HTTP_201_CREATED)


def _set_active(request, pk, active):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    schedule = ReportSchedule.objects.filter(organization=organization, pk=pk).first()
    if schedule is None:
        return Response({"detail": "Report schedule not found."}, status=404)
    if active and not _report_supported(request.user, schedule.report_code):
        return Response({"detail": "Report is no longer available."}, status=409)
    if schedule.is_active != active:
        schedule.is_active = active
        schedule.disabled_at = None if active else timezone.now()
        schedule.save(update_fields=["is_active", "disabled_at"])
        record_audit(request.user, f"report_schedule.{'enable' if active else 'disable'}", schedule)
    return Response(_payload(schedule))


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def disable_schedule(request, pk):
    return _set_active(request, pk, False)


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def enable_schedule(request, pk):
    return _set_active(request, pk, True)


@api_view(["GET"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def generations(request):
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    queryset = ReportGeneration.objects.filter(organization=organization)[:100]
    return Response(
        [
            {
                "id": item.id,
                "schedule": item.schedule_id,
                "report_code": item.report_code,
                "status": item.status,
                "row_count": item.row_count,
                "truncated": item.truncated,
                "generated_at": item.generated_at,
            }
            for item in queryset
            if _report_supported(request.user, item.report_code)
        ]
    )


@api_view(["POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def generate_schedule(request, pk):
    denied = _manager_or_403(request)
    if denied is not None:
        return denied
    organization, error = _organization_or_400(request)
    if error is not None:
        return error
    schedule = ReportSchedule.objects.filter(organization=organization, pk=pk, is_active=True).first()
    if schedule is None:
        return Response({"detail": "Active report schedule not found."}, status=404)
    if not _report_supported(request.user, schedule.report_code):
        return Response({"detail": "Report is no longer available."}, status=409)

    result = REPORT_BUILDERS[schedule.report_code](request.user)
    generation = ReportGeneration.objects.create(
        organization=organization,
        schedule=schedule,
        report_code=schedule.report_code,
        status=ReportGeneration.Status.SUCCEEDED,
        row_count=result["row_count"],
        truncated=result["truncated"],
        requested_by=request.user,
    )
    record_audit(
        request.user,
        "report_generation.create",
        generation,
        {
            "report": generation.report_code,
            "schedule_id": schedule.id,
            "row_count": generation.row_count,
            "truncated": generation.truncated,
        },
    )
    return Response(
        {
            "id": generation.id,
            "schedule": generation.schedule_id,
            "report_code": generation.report_code,
            "status": generation.status,
            "row_count": generation.row_count,
            "truncated": generation.truncated,
            "generated_at": generation.generated_at,
        },
        status=status.HTTP_201_CREATED,
    )
