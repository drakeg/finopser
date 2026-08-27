from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def root(request):
    return Response({
        "name": "finopser",
        "status": "ok",
        "version": "0.1.0-dev",
        "links": {"health": "/api/health/", "ready": "/api/ready/"},
    })


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        database = "ok"
        status = 200
    except Exception:
        database = "unavailable"
        status = 503
    return Response({"status": "ok" if status == 200 else "degraded", "database": database}, status=status)
