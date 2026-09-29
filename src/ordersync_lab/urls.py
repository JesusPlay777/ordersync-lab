from django.urls import include, path

from ordersync_lab.health import health

urlpatterns = [
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("ordersync_lab.orders.urls")),
]
