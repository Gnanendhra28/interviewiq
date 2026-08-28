.PHONY: help up down restart logs build test lint clean migrate

help:
	@echo "InterviewIQ Development Commands:"
	@echo "  make up        - Start all services using Docker Compose"
	@echo "  make down      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make logs      - View logs for all services"
	@echo "  make build     - Rebuild docker images"
	@echo "  make test      - Run backend unit and integration tests"
	@echo "  make lint      - Run code style & type checks"
	@echo "  make migrate   - Run database migrations via Alembic"

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

build:
	docker-compose build

test:
	pytest apps/api/app/modules/*/tests workers/tests -v

lint:
	ruff check apps/api workers
	mypy apps/api/app

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

migrate:
	cd apps/api && alembic upgrade head
