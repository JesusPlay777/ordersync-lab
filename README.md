# OrderSync Lab

OrderSync Lab is a public, fictional integration project for demonstrating reliable order processing, idempotency, recoverable failures, auditability, and an eventual AWS deployment.

The repository contains no employer code, production credentials, or real customer data. AWS resources are intentionally out of scope for the local preparation phase.

## Current milestone

`Phase 0 - Local preparation`

- Python 3.12 and Django 5.2 LTS.
- PostgreSQL 17 through Docker Compose.
- API exposed only on `127.0.0.1:8010`.
- PostgreSQL exposed only on `127.0.0.1:5433`.
- Database-backed health endpoint and smoke test.

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

Define the fictional Storefront-to-Warehouse contract, lifecycle states, idempotency rules, and acceptance scenarios before implementing business models.

