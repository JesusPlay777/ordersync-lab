import json
from copy import deepcopy
from pathlib import Path

import pytest
from django.test import override_settings

from ordersync_lab.lambda_worker import handler
from ordersync_lab.orders.models import SyncJob, WarehouseStock

pytestmark = pytest.mark.django_db(transaction=True)
EVENTS_DIR = Path(__file__).parent / "events"


class LambdaContext:
    aws_request_id = "test-worker-request-id"

    def __init__(self, remaining_ms=60_000):
        self.remaining_ms = remaining_ms

    def get_remaining_time_in_millis(self):
        return self.remaining_ms


def load_scheduler_event():
    return json.loads((EVENTS_DIR / "eventbridge_scheduler_worker.json").read_text())


def submit_orders(post_order, order_payload, count):
    for number in range(1, count + 1):
        payload = deepcopy(order_payload)
        payload["external_order_id"] = f"ORD-BATCH-{number:03d}"
        response = post_order(payload, key=f"mercury:ORD-BATCH-{number:03d}:v1")
        assert response.status_code == 202


@override_settings(ORDERSYNC_WORKER_BATCH_SIZE=2, ORDERSYNC_WORKER_MIN_REMAINING_MS=5_000)
def test_worker_handler_processes_only_the_configured_batch(post_order, order_payload):
    WarehouseStock.objects.update_or_create(
        sku="MUG-BLUE",
        defaults={"available_quantity": 25},
    )
    submit_orders(post_order, order_payload, count=3)

    result = handler(load_scheduler_event(), LambdaContext())

    assert result == {
        "request_id": "test-worker-request-id",
        "trigger": "ordersync.scheduler",
        "batch_limit": 2,
        "processed": 2,
        "outcomes": {"synced": 2, "failed": 0, "retry_pending": 0},
        "stopped_reason": "batch_limit",
    }
    assert SyncJob.objects.filter(status=SyncJob.Status.COMPLETED).count() == 2
    assert SyncJob.objects.filter(status=SyncJob.Status.PENDING).count() == 1
    assert WarehouseStock.objects.get(pk="MUG-BLUE").available_quantity == 21


@override_settings(ORDERSYNC_WORKER_BATCH_SIZE=10, ORDERSYNC_WORKER_MIN_REMAINING_MS=5_000)
def test_worker_handler_stops_when_no_due_job_exists():
    result = handler({}, LambdaContext())

    assert result["processed"] == 0
    assert result["trigger"] == "eventbridge-scheduler"
    assert result["outcomes"] == {"synced": 0, "failed": 0, "retry_pending": 0}
    assert result["stopped_reason"] == "queue_empty"


@override_settings(ORDERSYNC_WORKER_BATCH_SIZE=10, ORDERSYNC_WORKER_MIN_REMAINING_MS=5_000)
def test_worker_handler_preserves_pending_work_when_timeout_is_near(post_order, order_payload):
    submit_orders(post_order, order_payload, count=1)

    result = handler(load_scheduler_event(), LambdaContext(remaining_ms=5_000))

    assert result["processed"] == 0
    assert result["stopped_reason"] == "time_budget"
    assert SyncJob.objects.get().status == SyncJob.Status.PENDING
