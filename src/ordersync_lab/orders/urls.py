from django.urls import path

from ordersync_lab.orders.views import (
    InventoryProjectionListView,
    OrderCollectionView,
    OrderDetailView,
)

urlpatterns = [
    path("orders/", OrderCollectionView.as_view(), name="order-list"),
    path("orders/<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("inventory/", InventoryProjectionListView.as_view(), name="inventory-list"),
]
