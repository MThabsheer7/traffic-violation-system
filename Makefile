.PHONY: help dev-backend dev-frontend test lint docker-up docker-down export-model quantize seed

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Development ─────────────────────────────────────────

dev-backend: ## Start FastAPI dev server with hot-reload
	uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start Vite dev server
	cd frontend && npm run dev

dev: ## Start both backend and frontend (requires GNU parallel or run in two terminals)
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals"

# ─── Testing ─────────────────────────────────────────────

test: ## Run all tests
	python -m pytest tests/ -v

test-backend: ## Run backend tests only
	python -m pytest tests/backend/ -v

lint: ## Lint Python code with Ruff
	ruff check backend/ tests/ scripts/

lint-fix: ## Auto-fix lint issues
	ruff check --fix backend/ tests/ scripts/

# ─── Model Pipeline ─────────────────────────────────────

export-model: ## Export YOLO26n to OpenVINO IR format
	python scripts/export_model.py

quantize: ## Quantize model to INT8 via NNCF
	python scripts/quantize_model.py

# ─── Vision Engine ───────────────────────────────────────

run-vision: ## Run vision engine (set VIDEO_SOURCE in .env)
	python -m backend.vision.pipeline

# ─── Database ────────────────────────────────────────────

seed: ## Seed database with demo violation data
	python scripts/seed_demo_data.py

# ─── Docker ──────────────────────────────────────────────

docker-up: ## Build and start all containers
	docker compose up --build -d

docker-down: ## Stop all containers
	docker compose down

docker-logs: ## Tail container logs
	docker compose logs -f
