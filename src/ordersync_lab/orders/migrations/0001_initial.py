# Generated for OrderSync Lab phase 2.

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InventoryProjection",
            fields=[
                ("sku", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("available_quantity", models.PositiveIntegerField()),
                ("source", models.CharField(default="atlas-warehouse", max_length=64)),
                ("observed_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("source", models.CharField(max_length=64)),
                ("external_order_id", models.CharField(max_length=64)),
                ("request_fingerprint", models.CharField(max_length=64)),
                ("placed_at", models.DateTimeField()),
                ("currency", models.CharField(max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("received", "Received"),
                            ("processing", "Processing"),
                            ("retry_pending", "Retry pending"),
                            ("synced", "Synced"),
                            ("failed", "Failed"),
                        ],
                        default="received",
                        max_length=24,
                    ),
                ),
                ("failure_reason", models.CharField(blank=True, max_length=64)),
                ("correlation_id", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source", "external_order_id"),
                        name="unique_source_external_order",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="WarehouseFailurePlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_order_id", models.CharField(max_length=64, unique=True)),
                ("failures_remaining", models.PositiveSmallIntegerField(default=0)),
                ("error_code", models.CharField(default="atlas_unavailable", max_length=64)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="WarehouseStock",
            fields=[
                ("sku", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("available_quantity", models.PositiveIntegerField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("correlation_id", models.UUIDField()),
                ("event_type", models.CharField(max_length=64)),
                ("metadata", models.JSONField(default=dict)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_events",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["occurred_at", "id"],
                "indexes": [
                    models.Index(
                        fields=["order", "occurred_at"],
                        name="order_event_time_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="IdempotencyRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=64)),
                ("key", models.CharField(max_length=128)),
                ("request_fingerprint", models.CharField(max_length=64)),
                ("response_status", models.PositiveSmallIntegerField()),
                ("response_body", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="idempotency_records",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source", "key"),
                        name="unique_source_idempotency_key",
                    )
                ]
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(max_length=64)),
                ("quantity", models.PositiveSmallIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "warehouse_remaining_quantity",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
                "constraints": [
                    models.UniqueConstraint(fields=("order", "sku"), name="unique_order_sku"),
                    models.CheckConstraint(
                        condition=models.Q(("quantity__gte", 1)),
                        name="order_item_quantity_gte_1",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("unit_price__gte", 0)),
                        name="unit_price_gte_0",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SyncAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempt_number", models.PositiveSmallIntegerField()),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("started", "Started"),
                            ("succeeded", "Succeeded"),
                            ("rejected", "Rejected"),
                            ("retryable_failure", "Retryable failure"),
                            ("exhausted", "Exhausted"),
                            ("interrupted", "Interrupted"),
                        ],
                        default="started",
                        max_length=32,
                    ),
                ),
                ("error_code", models.CharField(blank=True, max_length=64)),
                ("next_retry_at", models.DateTimeField(blank=True, null=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["attempt_number"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("order", "attempt_number"),
                        name="unique_order_attempt_number",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SyncJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("retry_pending", "Retry pending"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=24,
                    ),
                ),
                ("attempts_count", models.PositiveSmallIntegerField(default=0)),
                ("available_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("last_error_code", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sync_job",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["status", "available_at"], name="due_sync_job_idx")
                ]
            },
        ),
        migrations.CreateModel(
            name="WarehouseReservation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("accepted", "Accepted"), ("rejected", "Rejected")],
                        max_length=16,
                    ),
                ),
                ("failure_reason", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservation",
                        to="orders.order",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("sku", models.CharField(max_length=64)),
                ("quantity", models.PositiveSmallIntegerField()),
                ("remaining_quantity", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "reservation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movements",
                        to="orders.warehousereservation",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("reservation", "sku"),
                        name="unique_reservation_sku",
                    )
                ]
            },
        ),
    ]
