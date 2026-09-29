import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSING = "processing", "Processing"
        RETRY_PENDING = "retry_pending", "Retry pending"
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=64)
    external_order_id = models.CharField(max_length=64)
    request_fingerprint = models.CharField(max_length=64)
    placed_at = models.DateTimeField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=24, choices=Status, default=Status.RECEIVED)
    failure_reason = models.CharField(max_length=64, blank=True)
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_order_id"],
                name="unique_source_external_order",
            )
        ]

    def __str__(self):
        return f"{self.source}:{self.external_order_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    sku = models.CharField(max_length=64)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    warehouse_remaining_quantity = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["order", "sku"], name="unique_order_sku"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="order_item_quantity_gte_1"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="unit_price_gte_0"),
        ]

    def __str__(self):
        return f"{self.order_id}:{self.sku}"


class IdempotencyRecord(models.Model):
    source = models.CharField(max_length=64)
    key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="idempotency_records")
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "key"], name="unique_source_idempotency_key")
        ]

    def __str__(self):
        return f"{self.source}:{self.key}"


class SyncJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        RETRY_PENDING = "retry_pending", "Retry pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="sync_job")
    status = models.CharField(max_length=24, choices=Status, default=Status.PENDING)
    attempts_count = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    locked_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["status", "available_at"], name="due_sync_job_idx")]

    def __str__(self):
        return f"{self.order_id}:{self.status}"


class SyncAttempt(models.Model):
    class Outcome(models.TextChoices):
        STARTED = "started", "Started"
        SUCCEEDED = "succeeded", "Succeeded"
        REJECTED = "rejected", "Rejected"
        RETRYABLE_FAILURE = "retryable_failure", "Retryable failure"
        EXHAUSTED = "exhausted", "Exhausted"
        INTERRUPTED = "interrupted", "Interrupted"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="attempts")
    attempt_number = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=32, choices=Outcome, default=Outcome.STARTED)
    error_code = models.CharField(max_length=64, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["attempt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "attempt_number"],
                name="unique_order_attempt_number",
            )
        ]

    def __str__(self):
        return f"{self.order_id}:attempt:{self.attempt_number}"


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="audit_events")
    correlation_id = models.UUIDField()
    event_type = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["occurred_at", "id"]
        indexes = [models.Index(fields=["order", "occurred_at"], name="order_event_time_idx")]

    def __str__(self):
        return f"{self.order_id}:{self.event_type}"


class WarehouseStock(models.Model):
    sku = models.CharField(max_length=64, primary_key=True)
    available_quantity = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sku


class WarehouseReservation(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="reservation")
    status = models.CharField(max_length=16, choices=Status)
    failure_reason = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_id}:{self.status}"


class StockMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(
        WarehouseReservation,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    sku = models.CharField(max_length=64)
    quantity = models.PositiveSmallIntegerField()
    remaining_quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reservation", "sku"], name="unique_reservation_sku")
        ]

    def __str__(self):
        return f"{self.reservation_id}:{self.sku}"


class InventoryProjection(models.Model):
    sku = models.CharField(max_length=64, primary_key=True)
    available_quantity = models.PositiveIntegerField()
    source = models.CharField(max_length=64, default="atlas-warehouse")
    observed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.sku


class WarehouseFailurePlan(models.Model):
    external_order_id = models.CharField(max_length=64, unique=True)
    failures_remaining = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=64, default="atlas_unavailable")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.external_order_id
