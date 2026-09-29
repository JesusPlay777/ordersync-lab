import pytest

from ordersync_lab.orders.models import AuditEvent, IdempotencyRecord, Order, SyncJob


@pytest.mark.django_db
def test_accepts_order_atomically(post_order, order_payload):
    response = post_order(order_payload)

    assert response.status_code == 202
    assert response.json()["status"] == "received"
    assert response.json()["status_url"].endswith(f"{response.json()['id']}/")
    assert response.headers["X-Correlation-ID"]

    order = Order.objects.get()
    assert order.items.count() == 1
    assert order.sync_job.status == SyncJob.Status.PENDING
    assert order.audit_events.values_list("event_type", flat=True).get() == "order.received"
    assert IdempotencyRecord.objects.get().order == order


@pytest.mark.django_db
def test_requires_idempotency_key(client, order_payload):
    response = client.post(
        "/api/v1/orders/",
        data=order_payload,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "idempotency_key" in response.json()
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_same_key_and_payload_replays_original_response(post_order, order_payload):
    first = post_order(order_payload)
    second = post_order(order_payload)

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert second.headers["Idempotency-Replayed"] == "true"
    assert Order.objects.count() == 1
    assert SyncJob.objects.count() == 1
    assert IdempotencyRecord.objects.count() == 1
    assert AuditEvent.objects.count() == 1


@pytest.mark.django_db
def test_same_key_with_changed_payload_returns_conflict(post_order, order_payload):
    post_order(order_payload)
    order_payload["items"][0]["quantity"] = 3

    response = post_order(order_payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_key_reused"
    assert Order.objects.get().items.get().quantity == 2


@pytest.mark.django_db
def test_same_external_order_with_new_key_resolves_existing_order(post_order, order_payload):
    first = post_order(order_payload)
    second = post_order(order_payload, key="mercury:ORD-1001:retry")

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.headers["Idempotency-Replayed"] == "true"
    assert Order.objects.count() == 1
    assert IdempotencyRecord.objects.count() == 2
    assert AuditEvent.objects.filter(event_type="order.duplicate_detected").count() == 1


@pytest.mark.django_db
def test_rejects_duplicate_skus(post_order, order_payload):
    order_payload["items"].append(order_payload["items"][0].copy())

    response = post_order(order_payload)

    assert response.status_code == 400
    assert "items" in response.json()
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_rejects_invalid_correlation_id(client, order_payload):
    response = client.post(
        "/api/v1/orders/",
        data=order_payload,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="mercury:ORD-1001:v1",
        HTTP_X_CORRELATION_ID="not-a-uuid",
    )

    assert response.status_code == 400
    assert "correlation_id" in response.json()
    assert Order.objects.count() == 0
