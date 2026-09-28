# OrderSync Lab

OrderSync Lab is a public, fictional integration project for demonstrating reliable order processing, idempotency, recoverable failures, auditability, and an eventual AWS deployment.

The repository contains no employer code, production credentials, or real customer data. AWS resources are intentionally out of scope for the local preparation phase.

## Current milestone

`Phase 1 - Domain definition complete`

- Python 3.12 and Django 5.2 LTS run locally with PostgreSQL 17 through Docker Compose.
- The fictional Mercury Storefront and Atlas Warehouse boundaries are defined.
- The order contract, lifecycle, inventory semantics, failure policy, and layered idempotency
  rules are documented.
- Eight reproducible acceptance scenarios define the evidence the implementation must provide.
- No business model or AWS resource has been created yet.

See the [domain definition](docs/domain.md), [local architecture](docs/architecture.md), and
[idempotency decision](docs/adr/0002-idempotent-order-synchronization.md).

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

## Quality checks

```bash
docker compose exec -T api python manage.py check
docker compose exec -T api pytest
docker compose exec -T api ruff check .
docker compose exec -T api ruff format --check .
```

## Stop locally

```bash
docker compose down
```

The PostgreSQL volume is retained. Removing it is a separate, destructive operation and is not part of the normal stop command.

## Next milestone

Implement the first local vertical slice: order ingestion, persistence, database-backed work,
the fake Atlas adapter, retries, inventory projection, audit events, and status queries.

