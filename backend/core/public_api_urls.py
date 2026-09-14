from django.urls import path

from . import compliance_api, policy_api, recommendation_api, report_api
from .api import CloudAccountViewSet, CloudResourceViewSet
from .cost_api import CostRecordViewSet
from .dashboard_api import operational_dashboard


urlpatterns = [
    path("dashboard/", operational_dashboard, name="public-v1-dashboard"),
    path(
        "cloud-accounts/",
        CloudAccountViewSet.as_view({"get": "list"}),
        name="public-v1-cloud-accounts",
    ),
    path(
        "resources/",
        CloudResourceViewSet.as_view({"get": "list"}),
        name="public-v1-resources",
    ),
    path(
        "costs/",
        CostRecordViewSet.as_view({"get": "list"}),
        name="public-v1-costs",
    ),
    path(
        "compliance/findings/",
        compliance_api.FindingViewSet.as_view({"get": "list"}),
        name="public-v1-compliance-findings",
    ),
    path(
        "policy-violations/",
        policy_api.ViolationViewSet.as_view({"get": "list"}),
        name="public-v1-policy-violations",
    ),
    path(
        "recommendations/",
        recommendation_api.RecommendationViewSet.as_view({"get": "list"}),
        name="public-v1-recommendations",
    ),
    path("reports/", report_api.catalog, name="public-v1-reports"),
]
