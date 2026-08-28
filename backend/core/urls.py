from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api import (
    AuditEventViewSet,
    CloudAccountViewSet,
    CloudResourceViewSet,
    InventorySyncViewSet,
    OrganizationNodeViewSet,
    OrganizationViewSet,
    ProjectViewSet,
    UserRoleViewSet,
)
from .compliance_api import (
    ControlViewSet,
    ExceptionViewSet,
    FindingViewSet,
    FrameworkViewSet,
    RunViewSet,
    evaluate as evaluate_compliance,
    summary as compliance_summary,
)
from .cost_api import CostRecordViewSet, CostSyncViewSet, sync_account_costs
from .dashboard_api import operational_dashboard
from .policy_api import (
    PolicyRunViewSet,
    PolicyViewSet,
    ViolationViewSet,
    evaluate as evaluate_policies,
    summary as policy_summary,
)

router = DefaultRouter()
router.register("organizations", OrganizationViewSet)
router.register("organization-nodes", OrganizationNodeViewSet)
router.register("projects", ProjectViewSet)
router.register("cloud-accounts", CloudAccountViewSet)
router.register("resources", CloudResourceViewSet, basename="resource")
router.register("inventory-syncs", InventorySyncViewSet, basename="inventory-sync")
router.register("costs", CostRecordViewSet, basename="cost")
router.register("cost-syncs", CostSyncViewSet, basename="cost-sync")
router.register("compliance/frameworks", FrameworkViewSet, basename="compliance-framework")
router.register("compliance/controls", ControlViewSet, basename="compliance-control")
router.register("compliance/findings", FindingViewSet, basename="compliance-finding")
router.register("compliance/exceptions", ExceptionViewSet, basename="compliance-exception")
router.register("compliance/runs", RunViewSet, basename="compliance-run")
router.register("policies", PolicyViewSet, basename="policy")
router.register("policy-violations", ViolationViewSet, basename="policy-violation")
router.register("policy-runs", PolicyRunViewSet, basename="policy-run")
router.register("audit-events", AuditEventViewSet)
router.register("users", UserRoleViewSet)

urlpatterns = [
    path("", views.root, name="api-root"),
    path("health/", views.health, name="health"),
    path("ready/", views.ready, name="ready"),
    path("auth/session/", views.session, name="session"),
    path("auth/me/", views.me, name="me"),
    path("dashboard/", operational_dashboard, name="operational-dashboard"),
    path("compliance/evaluate/", evaluate_compliance, name="compliance-evaluate"),
    path("compliance/summary/", compliance_summary, name="compliance-summary"),
    path("policies/evaluate/", evaluate_policies, name="policy-evaluate"),
    path("policies/summary/", policy_summary, name="policy-summary"),
    path("cloud-accounts/<int:pk>/sync-costs/", sync_account_costs, name="sync-account-costs"),
    path("", include(router.urls)),
]
