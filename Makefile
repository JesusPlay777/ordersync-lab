.PHONY: build up down ps logs check test lint format-check verify

build:
	docker compose build

up:
	docker compose up --build -d

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs --tail=100 api

check:
	docker compose exec -T api python manage.py check

test:
	docker compose exec -T api pytest

lint:
	docker compose exec -T api ruff check .

format-check:
	docker compose exec -T api ruff format --check .

verify: check test lint format-check

