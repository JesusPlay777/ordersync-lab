from copy import deepcopy

import pytest
from django.utils import timezone


@pytest.fixture
def order_payload():
    return {
        "source": "mercury-storefront",
        "external_order_id": "ORD-1001",
        "placed_at": timezone.now().isoformat(),
        "currency": "USD",
        "items": [
            {
                "sku": "MUG-BLUE",
                "quantity": 2,
                "unit_price": "12.50",
            }
        ],
    }


@pytest.fixture
def post_order(client):
    def _post(payload, key="mercury:ORD-1001:v1"):
        return client.post(
            "/api/v1/orders/",
            data=deepcopy(payload),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    return _post
