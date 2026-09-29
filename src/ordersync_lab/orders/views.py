import re
import uuid

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ordersync_lab.orders.models import InventoryProjection, Order
from ordersync_lab.orders.serializers import (
    InventoryProjectionSerializer,
    OrderDetailSerializer,
    OrderInputSerializer,
)
from ordersync_lab.orders.services import IngestionConflict, accept_order

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


class OrderCollectionView(APIView):
    def post(self, request):
        idempotency_key = request.headers.get("Idempotency-Key", "")
        if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
            return Response(
                {
                    "idempotency_key": [
                        "A key of 8 to 128 safe characters is required in Idempotency-Key."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        correlation_header = request.headers.get("X-Correlation-ID")
        try:
            correlation_id = uuid.UUID(correlation_header) if correlation_header else uuid.uuid4()
        except ValueError:
            return Response(
                {"correlation_id": ["X-Correlation-ID must be a valid UUID."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = accept_order(
                serializer.validated_data,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        except IngestionConflict as exc:
            return Response(
                {"error": {"code": exc.code, "detail": exc.detail}},
                status=status.HTTP_409_CONFLICT,
            )

        response = Response(result.body, status=result.status_code)
        if result.replayed:
            response["Idempotency-Replayed"] = "true"
        response["X-Correlation-ID"] = str(correlation_id)
        return response


class OrderDetailView(APIView):
    def get(self, request, order_id):  # noqa: ARG002
        order = get_object_or_404(
            Order.objects.prefetch_related("items", "attempts", "audit_events"),
            pk=order_id,
        )
        return Response(OrderDetailSerializer(order).data)


class InventoryProjectionListView(APIView):
    def get(self, request):  # noqa: ARG002
        projections = InventoryProjection.objects.order_by("sku")
        return Response({"results": InventoryProjectionSerializer(projections, many=True).data})
