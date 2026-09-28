from django.urls import path

from ordersync_lab.health import health

urlpatterns = [
    path("api/v1/health/", health, name="health"),
]
