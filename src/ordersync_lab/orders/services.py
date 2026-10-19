import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from ordersync_lab.orders.models import (
    AuditEvent,
    IdempotencyRecord,
    InventoryProjection,
    Order,
    OrderItem,
    SyncAttempt,
    SyncJob,
)
from ordersync_lab.orders.warehouse import (
    FakeAtlasWarehouse,
    ReservationResult,
    RetryableWarehouseError,
)


class IngestionConflict(Exception):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class AcceptanceResult:
    body: dict
    status_code: int
    replayed: bool


@dataclass(frozen=True)
class ClaimedJob:
    job_id: int
    order_id: uuid.UUID
    attempt_id: int
    attempt_number: int


def _canonical_payload(validated_data: dict) -> dict:
    return {
        "currency": validated_data["currency"],
        "external_order_id": validated_data["external_order_id"],
        "items": sorted(
            [
                {
                    "quantity": item["quantity"],
                    "sku": item["sku"],
                    "unit_price": format(Decimal(item["unit_price"]), ".2f"),
                }
                for item in validated_data["items"]
            ],
            key=lambda item: item["sku"],
        ),
        "placed_at": validated_data["placed_at"].astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "source": validated_data["source"],
    }


def request_fingerprint(validated_data: dict) -> str:
    encoded = json.dumps(
        _canonical_payload(validated_data),
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _postgres_advisory_locks(*values: str) -> None:
    if connection.vendor != "postgresql":
        return

    lock_ids = {
        int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], byteorder="big", signed=True)
        for value in values
    }
    with connection.cursor() as cursor:
        for lock_id in sorted(lock_ids):
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])


def _acceptance_body(order: Order) -> dict:
    return {
        "id": str(order.id),
        "source": order.source,
        "external_order_id": order.external_order_id,
        "status": order.status,
        "status_url": f"/api/v1/orders/{order.id}/",
    }


def _audit(order: Order, event_type: str, metadata: dict | None = None) -> AuditEvent:
    return AuditEvent.objects.create(
        order=order,
        correlation_id=order.correlation_id,
        event_type=event_type,
        metadata=metadata or {},
    )


def accept_order(
    validated_data: dict,
    *,
    idempotency_key: str,
    correlation_id: uuid.UUID,
) -> AcceptanceResult:
    source = validated_data["source"]
    external_order_id = validated_data["external_order_id"]
    fingerprint = request_fingerprint(validated_data)

    with transaction.atomic():
        _postgres_advisory_locks(
            f"idempotency:{source}:{idempotency_key}",
            f"order:{source}:{external_order_id}",
        )

        idempotency_record = (
            IdempotencyRecord.objects.select_related("order")
            .filter(source=source, key=idempotency_key)
            .first()
        )
        if idempotency_record:
            if idempotency_record.request_fingerprint != fingerprint:
                raise IngestionConflict(
                    "idempotency_key_reused",
                    "The idempotency key was already used with a different payload.",
                )
            return AcceptanceResult(
                body=idempotency_record.response_body,
                status_code=idempotency_record.response_status,
                replayed=True,
            )

        existing_order = (
            Order.objects.select_for_update()
            .filter(source=source, external_order_id=external_order_id)
            .first()
        )
        if existing_order:
            if existing_order.request_fingerprint != fingerprint:
                raise IngestionConflict(
                    "external_order_conflict",
                    "The external order ID already exists with a different payload.",
                )

            body = _acceptance_body(existing_order)
            IdempotencyRecord.objects.create(
                source=source,
                key=idempotency_key,
                request_fingerprint=fingerprint,
                order=existing_order,
                response_status=200,
                response_body=body,
            )
            _audit(
                existing_order,
                "order.duplicate_detected",
                {"reason": "external_order_replayed"},
            )
            return AcceptanceResult(body=body, status_code=200, replayed=True)

        order = Order.objects.create(
            source=source,
            external_order_id=external_order_id,
            request_fingerprint=fingerprint,
            placed_at=validated_data["placed_at"],
            currency=validated_data["currency"],
            correlation_id=correlation_id,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    sku=item["sku"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                )
                for item in validated_data["items"]
            ]
        )
        SyncJob.objects.create(order=order)
        _audit(order, "order.received", {"item_count": len(validated_data["items"])})

        body = _acceptance_body(order)
        IdempotencyRecord.objects.create(
            source=source,
            key=idempotency_key,
            request_fingerprint=fingerprint,
            order=order,
            response_status=202,
            response_body=body,
        )

        return AcceptanceResult(body=body, status_code=202, replayed=False)


def recover_stale_jobs(*, now=None) -> int:
    now = now or timezone.now()
    stale_before = now - timedelta(seconds=settings.ORDERSYNC_JOB_LOCK_TIMEOUT_SECONDS)
    recovered = 0

    with transaction.atomic():
        jobs = list(
            SyncJob.objects.select_for_update(skip_locked=True)
            .select_related("order")
            .filter(status=SyncJob.Status.PROCESSING, locked_at__lte=stale_before)
        )
        for job in jobs:
            attempt = (
                job.order.attempts.filter(outcome=SyncAttempt.Outcome.STARTED)
                .order_by("-attempt_number")
                .first()
            )
            if attempt:
                attempt.outcome = SyncAttempt.Outcome.INTERRUPTED
                attempt.error_code = "worker_interrupted"
                attempt.finished_at = now
                attempt.save(update_fields=["outcome", "error_code", "finished_at"])

            if job.attempts_count >= settings.ORDERSYNC_MAX_ATTEMPTS:
                job.status = SyncJob.Status.FAILED
                job.last_error_code = "retry_exhausted"
                job.order.status = Order.Status.FAILED
                job.order.failure_reason = "retry_exhausted"
                _audit(job.order, "order.failed", {"reason": "retry_exhausted"})
            else:
                job.status = SyncJob.Status.RETRY_PENDING
                job.available_at = now
                job.last_error_code = "worker_interrupted"
                job.order.status = Order.Status.RETRY_PENDING
                _audit(
                    job.order,
                    "sync.retry_scheduled",
                    {"reason": "worker_interrupted", "next_retry_at": now.isoformat()},
                )

            job.locked_at = None
            job.save(
                update_fields=[
                    "status",
                    "available_at",
                    "locked_at",
                    "last_error_code",
                    "updated_at",
                ]
            )
            job.order.save(update_fields=["status", "failure_reason", "updated_at"])
            recovered += 1

    return recovered


def claim_next_job(*, now=None) -> ClaimedJob | None:
    now = now or timezone.now()
    with transaction.atomic():
        job = (
            SyncJob.objects.select_for_update(skip_locked=True)
            .select_related("order")
            .filter(
                status__in=[SyncJob.Status.PENDING, SyncJob.Status.RETRY_PENDING],
                available_at__lte=now,
            )
            .order_by("available_at", "id")
            .first()
        )
        if not job:
            return None

        job.attempts_count += 1
        job.status = SyncJob.Status.PROCESSING
        job.locked_at = now
        job.save(update_fields=["attempts_count", "status", "locked_at", "updated_at"])

        job.order.status = Order.Status.PROCESSING
        job.order.failure_reason = ""
        job.order.save(update_fields=["status", "failure_reason", "updated_at"])

        attempt = SyncAttempt.objects.create(
            order=job.order,
            attempt_number=job.attempts_count,
            started_at=now,
        )
        _audit(job.order, "sync.attempt_started", {"attempt": job.attempts_count})

        return ClaimedJob(
            job_id=job.id,
            order_id=job.order_id,
            attempt_id=attempt.id,
            attempt_number=job.attempts_count,
        )


def _finalize_reservation(claimed: ClaimedJob, result: ReservationResult) -> str:
    now = timezone.now()
    with transaction.atomic():
        job = SyncJob.objects.select_for_update().select_related("order").get(pk=claimed.job_id)
        attempt = SyncAttempt.objects.select_for_update().get(pk=claimed.attempt_id)
        order = job.order

        if result.accepted:
            remaining_by_sku = {line.sku: line.remaining_quantity for line in result.lines}
            items = list(order.items.all())
            for item in items:
                item.warehouse_remaining_quantity = remaining_by_sku[item.sku]
            OrderItem.objects.bulk_update(items, ["warehouse_remaining_quantity"])

            for line in result.lines:
                InventoryProjection.objects.update_or_create(
                    sku=line.sku,
                    defaults={
                        "available_quantity": line.remaining_quantity,
                        "source": "atlas-warehouse",
                        "observed_at": now,
                    },
                )

            attempt.outcome = SyncAttempt.Outcome.SUCCEEDED
            job.status = SyncJob.Status.COMPLETED
            job.last_error_code = ""
            order.status = Order.Status.SYNCED
            order.failure_reason = ""
            _audit(
                order,
                "warehouse.reservation_succeeded",
                {
                    "attempt": claimed.attempt_number,
                    "lines": [
                        {"sku": line.sku, "remaining_quantity": line.remaining_quantity}
                        for line in result.lines
                    ],
                },
            )
            _audit(order, "inventory.projection_updated", {"sku_count": len(result.lines)})
            _audit(order, "order.synced")
            outcome = "synced"
        else:
            attempt.outcome = SyncAttempt.Outcome.REJECTED
            attempt.error_code = result.failure_reason
            job.status = SyncJob.Status.FAILED
            job.last_error_code = result.failure_reason
            order.status = Order.Status.FAILED
            order.failure_reason = result.failure_reason
            _audit(
                order,
                "warehouse.reservation_rejected",
                {"reason": result.failure_reason},
            )
            _audit(order, "order.failed", {"reason": result.failure_reason})
            outcome = "failed"

        attempt.finished_at = now
        attempt.save(update_fields=["outcome", "error_code", "finished_at"])
        job.locked_at = None
        job.save(update_fields=["status", "locked_at", "last_error_code", "updated_at"])
        order.save(update_fields=["status", "failure_reason", "updated_at"])
        return outcome


def _schedule_retry(claimed: ClaimedJob, error_code: str) -> str:
    now = timezone.now()
    with transaction.atomic():
        job = SyncJob.objects.select_for_update().select_related("order").get(pk=claimed.job_id)
        attempt = SyncAttempt.objects.select_for_update().get(pk=claimed.attempt_id)
        order = job.order

        attempt.finished_at = now
        attempt.error_code = error_code
        job.locked_at = None
        job.last_error_code = error_code

        if job.attempts_count >= settings.ORDERSYNC_MAX_ATTEMPTS:
            attempt.outcome = SyncAttempt.Outcome.EXHAUSTED
            job.status = SyncJob.Status.FAILED
            order.status = Order.Status.FAILED
            order.failure_reason = "retry_exhausted"
            _audit(
                order,
                "order.failed",
                {"reason": "retry_exhausted", "last_error_code": error_code},
            )
            outcome = "failed"
        else:
            delay_index = min(
                job.attempts_count - 1,
                len(settings.ORDERSYNC_RETRY_DELAYS_SECONDS) - 1,
            )
            retry_at = now + timedelta(seconds=settings.ORDERSYNC_RETRY_DELAYS_SECONDS[delay_index])
            attempt.outcome = SyncAttempt.Outcome.RETRYABLE_FAILURE
            attempt.next_retry_at = retry_at
            job.status = SyncJob.Status.RETRY_PENDING
            job.available_at = retry_at
            order.status = Order.Status.RETRY_PENDING
            order.failure_reason = ""
            _audit(
                order,
                "sync.retry_scheduled",
                {
                    "attempt": claimed.attempt_number,
                    "error_code": error_code,
                    "next_retry_at": retry_at.isoformat(),
                },
            )
            outcome = "retry_pending"

        attempt.save(
            update_fields=[
                "outcome",
                "error_code",
                "finished_at",
                "next_retry_at",
            ]
        )
        job.save(
            update_fields=[
                "status",
                "available_at",
                "locked_at",
                "last_error_code",
                "updated_at",
            ]
        )
        order.save(update_fields=["status", "failure_reason", "updated_at"])
        return outcome


def process_next_job(*, adapter=None, now=None, recover_stale=True) -> str | None:
    if recover_stale:
        recover_stale_jobs(now=now)
    claimed = claim_next_job(now=now)
    if not claimed:
        return None

    warehouse = adapter or FakeAtlasWarehouse()
    try:
        result = warehouse.reserve(claimed.order_id)
    except RetryableWarehouseError as exc:
        return _schedule_retry(claimed, exc.error_code)
    return _finalize_reservation(claimed, result)
