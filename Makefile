.PHONY: test lint migrate seed up down build help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

test: ## Run backend tests (pytest)
	cd backend && PYTHONPATH=. pytest -q

lint: ## Run backend (ruff) and frontend (eslint) linters
	cd backend && ruff check .
	cd frontend && npm run lint

migrate: ## Run Alembic migrations against the current DATABASE_URL
	cd backend && alembic upgrade head

seed: ## Seed the database with an admin user and sample data
	python3 scripts/seed_data.py

up: ## Start the full Docker Compose development stack
	docker compose up -d --build

down: ## Stop the Docker Compose development stack
	docker compose down

build: ## Build all Docker Compose services
	docker compose build
