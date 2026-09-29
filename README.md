# OrderSync Lab

OrderSync Lab is a public, fictional integration project for demonstrating reliable order
processing, idempotency, recoverable failures, auditability, and an eventual AWS deployment.

The repository contains no employer code, production credentials, or real customer data. AWS
resources remain out of scope until the local workflow is complete and measurable.

## Current milestone

`Phase 3 - AWS architecture evaluated; not deployed`

- Python 3.12 and Django 5.2 LTS run locally with PostgreSQL 17 through Docker Compose.
- The API atomically accepts immutable Mercury Storefront orders.
- Layered idempotency prevents duplicate orders, jobs, reservations, and stock movements.
- A separate worker processes durable PostgreSQL jobs through the fake Atlas Warehouse adapter.
- Atlas supports all-or-nothing stock reservations, deterministic failures, and safe retries.
- Order status exposes attempts, inventory results, correlation IDs, and audit events.
- Fourteen automated tests cover the first slice; no AWS resource has been created.
- The first AWS baseline is documented as API Gateway, Lambda, private RDS PostgreSQL, ECR,
  Parameter Store, Secrets Manager, CloudWatch, and EventBridge Scheduler.
- The existing PostgreSQL job table remains the durable queue until measured requirements
  justify an outbox-to-SQS design.

See the [domain definition](docs/domain.md), [local architecture](docs/architecture.md), and
[AWS architecture evaluation](docs/aws-architecture-evaluation.md). The selected cloud baseline
is recorded in [ADR 0003](docs/adr/0003-serverless-aws-baseline.md).

## Requirements

- Docker Desktop with WSL integration.
- Docker Compose v2 or later.
- GNU Make is optional; every command can also be run directly with Docker Compose.

## Start locally

Copy the local configuration if you want to override the safe defaults:

```bash
cp .env.example .env
```

Build and start the stack:

```bash
docker compose up --build -d
docker compose ps
```

Verify the application:

```bash
curl http://127.0.0.1:8010/api/v1/health/
```

Expected response:

```json
{"service":"ordersync-api","status":"ok","database":"ok"}
```

The Compose stack contains `api`, `worker`, and `db`. The worker processes accepted orders in
the background.

## Run the happy path

Submit a fictional order:

```bash
curl --request POST http://127.0.0.1:8010/api/v1/orders/ \
  --header 'Content-Type: application/json' \
  --header 'Idempotency-Key: mercury:ORD-DEMO-001:v1' \
  --data '{
    "source": "mercury-storefront",
    "external_order_id": "ORD-DEMO-001",
    "placed_at": "2026-09-29T17:45:00Z",
    "currency": "USD",
    "items": [{"sku": "MUG-BLUE", "quantity": 2, "unit_price": "12.50"}]
  }'
```

Use the returned `status_url` to inspect the result and audit timeline. The inventory projection
is available at `GET /api/v1/inventory/`.

To demonstrate a recoverable Atlas outage before submitting a new external order ID:

```bash
docker compose exec -T api \
  python manage.py configure_atlas_failure ORD-RETRY-001 --failures 1
```

The order first enters `retry_pending`; the worker then retries it without decrementing stock
twice.

## Quality checks

```bash
docker compose exec -T api python manage.py check
docker compose exec -T api python manage.py makemigrations --check --dry-run
docker compose exec -T api pytest
docker compose exec -T api ruff check .
docker compose exec -T api ruff format --check .
```

## Stop locally

```bash
docker compose down
```

The PostgreSQL volume is retained. Removing it is a separate, destructive operation and is not
part of the normal stop command.

## Next milestone

Adapt the Django API and bounded worker for Lambda, add tests for their AWS event handlers, and
prepare infrastructure as code for review. Planning or inspecting that infrastructure will not
authorize applying it; deployment remains behind the cost and security gate in ADR 0003.

