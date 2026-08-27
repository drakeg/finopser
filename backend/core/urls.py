from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api import (
    AuditEventViewSet,
    CloudAccountViewSet,
    OrganizationNodeViewSet,
    OrganizationViewSet,
    ProjectViewSet,
    UserRoleViewSet,
)

router = DefaultRouter()
router.register("organizations", OrganizationViewSet)
router.register("organization-nodes", OrganizationNodeViewSet)
router.register("projects", ProjectViewSet)
router.register("cloud-accounts", CloudAccountViewSet)
router.register("audit-events", AuditEventViewSet)
router.register("users", UserRoleViewSet)

urlpatterns = [
    path("", views.root, name="api-root"),
    path("health/", views.health, name="health"),
    path("ready/", views.ready, name="ready"),
    path("auth/session/", views.session, name="session"),
    path("auth/me/", views.me, name="me"),
    path("", include(router.urls)),
]
