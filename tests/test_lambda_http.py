import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from ordersync_lab.lambda_http import handler
from ordersync_lab.orders.models import IdempotencyRecord, Order, SyncJob

pytestmark = pytest.mark.django_db(transaction=True)
EVENTS_DIR = Path(__file__).parent / "events"


def load_http_event():
    return json.loads((EVENTS_DIR / "api_gateway_http_v2_health.json").read_text())


def lambda_context():
    return SimpleNamespace(
        aws_request_id="test-lambda-request-id",
        function_name="ordersync-api-test",
    )


def test_http_handler_adapts_health_request():
    response = handler(load_http_event(), lambda_context())

    assert response["statusCode"] == 200
    assert response["isBase64Encoded"] is False
    assert response["headers"]["content-type"].startswith("application/json")
    assert json.loads(response["body"]) == {
        "service": "ordersync-api",
        "status": "ok",
        "database": "ok",
    }


def test_http_handler_preserves_order_headers_and_body(order_payload):
    event = deepcopy(load_http_event())
    event["routeKey"] = "POST /api/v1/orders/"
    event["rawPath"] = "/api/v1/orders/"
    event["headers"].update(
        {
            "content-type": "application/json",
            "idempotency-key": "mercury:ORD-1001:v1",
            "x-correlation-id": "7705c82f-0d4b-4d6e-b036-ad1e4688717c",
        }
    )
    event["requestContext"]["http"].update({"method": "POST", "path": "/api/v1/orders/"})
    event["requestContext"]["routeKey"] = "POST /api/v1/orders/"
    event["body"] = json.dumps(order_payload)

    assert "content-length" not in event["headers"]
    response = handler(event, lambda_context())
    body = json.loads(response["body"])

    assert response["statusCode"] == 202
    assert response["headers"]["x-correlation-id"] == event["headers"]["x-correlation-id"]
    assert body["status"] == "received"
    assert body["status_url"].endswith(f"{body['id']}/")
    assert Order.objects.get().sync_job.status == SyncJob.Status.PENDING
    assert str(IdempotencyRecord.objects.get().order_id) == body["id"]
