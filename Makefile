.PHONY: test lint migrate seed up down build help \
        deploy prod-up prod-down prod-logs prod-migrate prod-seed

# Production stack = base compose + prod override (resource limits, Caddy, closed ports).
COMPOSE_PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

test: ## Run backend tests (pytest)
	cd backend && PYTHONPATH=. pytest -q

lint: ## Run backend (ruff) and frontend (eslint) linters
	cd backend && ruff check .
	cd frontend && npm run lint

migrate: ## Run Alembic migrations against the current DATABASE_URL
	cd backend && alembic upgrade head

seed: ## Seed the database with a demo firm, users, and sample data
	cd backend && python3 -m app.seed

up: ## Start the full Docker Compose development stack
	docker compose up -d --build

down: ## Stop the Docker Compose development stack
	docker compose down

build: ## Build all Docker Compose services
	docker compose build

# ── Production deploy ─────────────────────────────────────────────────────────

deploy: ## Full production deploy: build+start, migrate, seed (idempotent). Set DOMAIN first.
	@if [ -z "$$DOMAIN" ] && ! grep -q '^DOMAIN=' .env 2>/dev/null; then \
		echo "ERROR: DOMAIN is not set and not found in .env — Caddy would issue TLS for 'yourdomain.com'."; \
		echo "Fix:   export DOMAIN=yourdomain.com   (or uncomment DOMAIN in .env)"; \
		exit 1; \
	fi
	$(COMPOSE_PROD) up -d --build --wait
	$(COMPOSE_PROD) exec -T fastapi alembic upgrade head
	$(COMPOSE_PROD) exec -T fastapi python -m app.seed
	@echo ""
	@echo "Deployed → https://app.$${DOMAIN:-yourdomain.com}"
	@echo "Demo login: demo@operatoros.in / OperatorOS#2026"

prod-up: ## Build & start the production stack only (no migrate/seed)
	$(COMPOSE_PROD) up -d --build --wait

prod-down: ## Stop the production stack
	$(COMPOSE_PROD) down

prod-logs: ## Tail logs from the production stack
	$(COMPOSE_PROD) logs -f --tail=100

prod-migrate: ## Run Alembic migrations inside the running fastapi container
	$(COMPOSE_PROD) exec -T fastapi alembic upgrade head

prod-seed: ## Seed demo data inside the running fastapi container
	$(COMPOSE_PROD) exec -T fastapi python -m app.seed
