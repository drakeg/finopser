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
from .cost_api import CostRecordViewSet, CostSyncViewSet, sync_account_costs
from .dashboard_api import operational_dashboard

router = DefaultRouter()
router.register("organizations", OrganizationViewSet)
router.register("organization-nodes", OrganizationNodeViewSet)
router.register("projects", ProjectViewSet)
router.register("cloud-accounts", CloudAccountViewSet)
router.register("resources", CloudResourceViewSet, basename="resource")
router.register("inventory-syncs", InventorySyncViewSet, basename="inventory-sync")
router.register("costs", CostRecordViewSet, basename="cost")
router.register("cost-syncs", CostSyncViewSet, basename="cost-sync")
router.register("audit-events", AuditEventViewSet)
router.register("users", UserRoleViewSet)

urlpatterns = [
    path("", views.root, name="api-root"),
    path("health/", views.health, name="health"),
    path("ready/", views.ready, name="ready"),
    path("auth/session/", views.session, name="session"),
    path("auth/me/", views.me, name="me"),
    path("dashboard/", operational_dashboard, name="operational-dashboard"),
    path("cloud-accounts/<int:pk>/sync-costs/", sync_account_costs, name="sync-account-costs"),
    path("", include(router.urls)),
]
