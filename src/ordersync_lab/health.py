from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):  # noqa: ARG001
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # pragma: no cover - exercised when the dependency is unavailable
        return JsonResponse(
            {"service": "ordersync-api", "status": "unavailable", "database": "error"},
            status=503,
        )

    return JsonResponse({"service": "ordersync-api", "status": "ok", "database": "ok"})
