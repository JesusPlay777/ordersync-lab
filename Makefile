.PHONY: build up down ps logs check migrations-check test lint format-check verify \
	sam-prepare-env sam-validate sam-build sam-local-api-invoke sam-local-worker-invoke \
	sam-local-migration-plan \
	sam-local-api infra-validate cloud-validate ecr-validate cloud-image-build

SAM_CLI_TELEMETRY ?= 0
export SAM_CLI_TELEMETRY
SAM_PORT ?= 3000

build:
	docker compose build

up:
	docker compose up --build -d

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs --tail=100 api worker

check:
	docker compose exec -T api python manage.py check

migrations-check:
	docker compose exec -T api python manage.py makemigrations --check --dry-run

test:
	docker compose exec -T api pytest

lint:
	docker compose exec -T api ruff check .

format-check:
	docker compose exec -T api ruff format --check .

verify: check migrations-check test lint format-check

sam-prepare-env:
	test -f sam-env.local.json || cp sam-env.example.json sam-env.local.json

sam-validate:
	sam validate --lint

infra-validate:
	sam validate --lint --template-file infra/network-database.yaml --region us-east-2

cloud-validate:
	sam validate --lint --template-file infra/cloud-functions.yaml --region us-east-2

ecr-validate:
	sam validate --lint --template-file infra/ecr-repository.yaml --region us-east-2

cloud-image-build:
	docker buildx build --platform linux/amd64 --provenance=false --load \
		-f Dockerfile.lambda -t ordersync-lab:cloud-candidate .

sam-build:
	sam build

sam-local-api-invoke: sam-prepare-env sam-build
	sam local invoke OrderSyncApiFunction \
		--event tests/events/api_gateway_http_v2_health.json

sam-local-worker-invoke: sam-prepare-env sam-build
	sam local invoke OrderSyncWorkerFunction \
		--event tests/events/eventbridge_scheduler_worker.json

sam-local-migration-plan: sam-prepare-env sam-build
	sam local invoke OrderSyncMigrationFunction \
		--event tests/events/migration_plan.json

sam-local-api: sam-prepare-env sam-build
	sam local start-api --port $(SAM_PORT)
