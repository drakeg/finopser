from django.conf import settings
from django.db import connection
from redis import Redis
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .rbac import MANAGED_ROLES


@api_view(["GET"])
def root(request):
    return Response(
        {
            "name": "finopser",
            "status": "ok",
            "version": "0.2.0-dev",
            "links": {
                "health": "/api/health/",
                "ready": "/api/ready/",
                "session": "/api/auth/session/",
                "me": "/api/auth/me/",
                "organizations": "/api/organizations/",
                "organization_nodes": "/api/organization-nodes/",
                "projects": "/api/projects/",
                "audit_events": "/api/audit-events/",
            },
        }
    )


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def ready(request):
    checks = {"database": "unavailable", "redis": "unavailable"}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        pass
    try:
        Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception:
        pass
    is_ready = all(value == "ok" for value in checks.values())
    return Response({"status": "ok" if is_ready else "degraded", "checks": checks}, status=200 if is_ready else 503)


@api_view(["GET"])
def session(request):
    user = request.user
    return Response({"authenticated": user.is_authenticated, "username": user.get_username() if user.is_authenticated else None})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    roles = list(request.user.groups.filter(name__in=MANAGED_ROLES).values_list("name", flat=True))
    return Response({"id": request.user.id, "username": request.user.username, "email": request.user.email, "roles": roles})
