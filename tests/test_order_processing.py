from datetime import timedelta

import pytest
from django.utils import timezone

from ordersync_lab.orders.models import (
    InventoryProjection,
    Order,
    StockMovement,
    SyncAttempt,
    WarehouseFailurePlan,
    WarehouseReservation,
    WarehouseStock,
)
from ordersync_lab.orders.services import claim_next_job, process_next_job
from ordersync_lab.orders.warehouse import FakeAtlasWarehouse


def make_retry_due(order):
    job = order.sync_job
    job.available_at = timezone.now() - timedelta(seconds=1)
    job.save(update_fields=["available_at"])


@pytest.mark.django_db
def test_happy_path_reserves_stock_once_and_exposes_evidence(
    client,
    post_order,
    order_payload,
):
    WarehouseStock.objects.update_or_create(
        sku="MUG-BLUE",
        defaults={"available_quantity": 25},
    )
    accepted = post_order(order_payload)

    assert process_next_job() == "synced"

    order = Order.objects.get()
    assert order.status == Order.Status.SYNCED
    assert order.items.get().warehouse_remaining_quantity == 23
    assert WarehouseStock.objects.get(pk="MUG-BLUE").available_quantity == 23
    assert InventoryProjection.objects.get(pk="MUG-BLUE").available_quantity == 23
    assert StockMovement.objects.count() == 1
    assert WarehouseReservation.objects.count() == 1

    repeated_result = FakeAtlasWarehouse().reserve(order.id)
    assert repeated_result.accepted is True
    assert WarehouseStock.objects.get(pk="MUG-BLUE").available_quantity == 23
    assert StockMovement.objects.count() == 1

    detail = client.get(accepted.json()["status_url"])
    assert detail.status_code == 200
    assert detail.json()["status"] == "synced"
    assert detail.json()["attempts"][0]["outcome"] == "succeeded"
    assert detail.json()["items"][0]["warehouse_remaining_quantity"] == 23
    assert detail.json()["audit_events"][-1]["event_type"] == "order.synced"

    inventory = client.get("/api/v1/inventory/")
    assert inventory.status_code == 200
    assert inventory.json()["results"][0]["available_quantity"] == 23


@pytest.mark.django_db
def test_insufficient_stock_is_terminal_and_has_no_movement(post_order, order_payload):
    WarehouseStock.objects.update_or_create(
        sku="MUG-BLUE",
        defaults={"available_quantity": 1},
    )
    post_order(order_payload)

    assert process_next_job() == "failed"

    order = Order.objects.get()
    assert order.status == Order.Status.FAILED
    assert order.failure_reason == "insufficient_stock"
    assert WarehouseStock.objects.get(pk="MUG-BLUE").available_quantity == 1
    assert StockMovement.objects.count() == 0
    assert order.attempts.get().outcome == SyncAttempt.Outcome.REJECTED


@pytest.mark.django_db
def test_transient_failure_retries_then_succeeds_without_duplicate_stock(
    post_order,
    order_payload,
):
    WarehouseStock.objects.update_or_create(
        sku="MUG-BLUE",
        defaults={"available_quantity": 25},
    )
    WarehouseFailurePlan.objects.create(
        external_order_id=order_payload["external_order_id"],
        failures_remaining=1,
    )
    post_order(order_payload)

    assert process_next_job() == "retry_pending"
    order = Order.objects.get()
    assert order.status == Order.Status.RETRY_PENDING
    assert WarehouseStock.objects.get(pk="MUG-BLUE").available_quantity == 25
    assert StockMovement.objects.count() == 0

    make_retry_due(order)
    assert process_next_job() == "synced"

    order.refresh_from_db()
    assert order.status == Order.Status.SYNCED
    assert list(order.attempts.values_list("outcome", flat=True)) == [
        SyncAttempt.Outcome.RETRYABLE_FAILURE,
        SyncAttempt.Outcome.SUCCEEDED,
    ]
    assert WarehouseStock.objects.get(pk="MUG-BLUE").available_quantity == 23
    assert StockMovement.objects.count() == 1


@pytest.mark.django_db
def test_three_transient_failures_exhaust_retry_budget(post_order, order_payload):
    WarehouseStock.objects.update_or_create(
        sku="MUG-BLUE",
        defaults={"available_quantity": 25},
    )
    WarehouseFailurePlan.objects.create(
        external_order_id=order_payload["external_order_id"],
        failures_remaining=3,
    )
    post_order(order_payload)

    assert process_next_job() == "retry_pending"
    order = Order.objects.get()
    make_retry_due(order)
    assert process_next_job() == "retry_pending"
    make_retry_due(order)
    assert process_next_job() == "failed"

    order.refresh_from_db()
    assert order.status == Order.Status.FAILED
    assert order.failure_reason == "retry_exhausted"
    assert list(order.attempts.values_list("outcome", flat=True)) == [
        SyncAttempt.Outcome.RETRYABLE_FAILURE,
        SyncAttempt.Outcome.RETRYABLE_FAILURE,
        SyncAttempt.Outcome.EXHAUSTED,
    ]
    assert WarehouseStock.objects.get(pk="MUG-BLUE").available_quantity == 25
    assert StockMovement.objects.count() == 0


@pytest.mark.django_db
def test_stale_processing_job_is_recovered_after_worker_interruption(
    post_order,
    order_payload,
):
    WarehouseStock.objects.update_or_create(
        sku="MUG-BLUE",
        defaults={"available_quantity": 25},
    )
    post_order(order_payload)
    order = Order.objects.get()
    stale_time = timezone.now() - timedelta(minutes=10)
    job = order.sync_job
    job.available_at = stale_time
    job.save(update_fields=["available_at"])

    abandoned_claim = claim_next_job(now=stale_time)
    assert abandoned_claim is not None
    assert order.attempts.get().outcome == SyncAttempt.Outcome.STARTED

    assert process_next_job(now=timezone.now()) == "synced"

    order.refresh_from_db()
    assert order.status == Order.Status.SYNCED
    assert list(order.attempts.values_list("outcome", flat=True)) == [
        SyncAttempt.Outcome.INTERRUPTED,
        SyncAttempt.Outcome.SUCCEEDED,
    ]
    assert StockMovement.objects.count() == 1
