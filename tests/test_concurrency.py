import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from django.db import close_old_connections

from ordersync_lab.orders.models import IdempotencyRecord, Order, SyncJob
from ordersync_lab.orders.serializers import OrderInputSerializer
from ordersync_lab.orders.services import accept_order


@pytest.mark.django_db(transaction=True)
def test_concurrent_replays_create_one_order_and_job(order_payload):
    barrier = threading.Barrier(2)

    def submit():
        close_old_connections()
        serializer = OrderInputSerializer(data=deepcopy(order_payload))
        serializer.is_valid(raise_exception=True)
        barrier.wait()
        try:
            return accept_order(
                serializer.validated_data,
                idempotency_key="mercury:ORD-1001:v1",
                correlation_id=uuid.uuid4(),
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: submit(), range(2)))

    assert {result.status_code for result in results} == {202}
    assert sorted(result.replayed for result in results) == [False, True]
    assert Order.objects.count() == 1
    assert SyncJob.objects.count() == 1
    assert IdempotencyRecord.objects.count() == 1
