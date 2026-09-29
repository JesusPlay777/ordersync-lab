from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from ordersync_lab.orders.models import (
    AuditEvent,
    InventoryProjection,
    Order,
    OrderItem,
    SyncAttempt,
)


class OrderItemInputSerializer(serializers.Serializer):
    sku = serializers.RegexField(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
    quantity = serializers.IntegerField(min_value=1, max_value=999)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class OrderInputSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=["mercury-storefront"])
    external_order_id = serializers.RegexField(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    placed_at = serializers.DateTimeField()
    currency = serializers.ChoiceField(choices=["USD"])
    items = OrderItemInputSerializer(many=True, allow_empty=False, max_length=100)

    def validate_placed_at(self, value):
        if value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError("Must not be more than five minutes in the future.")
        return value

    def validate_items(self, value):
        skus = [item["sku"] for item in value]
        if len(skus) != len(set(skus)):
            raise serializers.ValidationError("Each SKU may appear only once per order.")
        return value


class OrderItemOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["sku", "quantity", "unit_price", "warehouse_remaining_quantity"]


class SyncAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncAttempt
        fields = [
            "attempt_number",
            "started_at",
            "finished_at",
            "outcome",
            "error_code",
            "next_retry_at",
        ]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "event_type", "correlation_id", "occurred_at", "metadata"]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemOutputSerializer(many=True)
    attempts = SyncAttemptSerializer(many=True)
    audit_events = AuditEventSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "source",
            "external_order_id",
            "placed_at",
            "currency",
            "status",
            "failure_reason",
            "correlation_id",
            "created_at",
            "updated_at",
            "items",
            "attempts",
            "audit_events",
        ]


class InventoryProjectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryProjection
        fields = ["sku", "available_quantity", "source", "observed_at"]
