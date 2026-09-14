from django.urls import path

from .api import CloudAccountViewSet, CloudResourceViewSet
from .compliance_api import FindingViewSet
from .cost_api import CostRecordViewSet
from .dashboard_api import operational_dashboard
from .policy_api import ViolationViewSet
from .recommendation_api import RecommendationViewSet
from .report_api import catalog


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
        FindingViewSet.as_view({"get": "list"}),
        name="public-v1-compliance-findings",
    ),
    path(
        "policy-violations/",
        ViolationViewSet.as_view({"get": "list"}),
        name="public-v1-policy-violations",
    ),
    path(
        "recommendations/",
        RecommendationViewSet.as_view({"get": "list"}),
        name="public-v1-recommendations",
    ),
    path("reports/", catalog, name="public-v1-reports"),
]
