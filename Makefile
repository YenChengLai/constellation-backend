# ==============================================================================
# Makefile for Constellation Backend Monorepo
# ==============================================================================

# .PHONY 告訴 make，這些 target 不是真正的檔案，而是指令。
.PHONY: help install setup-env run run-auth run-expense db-seed lint test clean

# 預設執行的 target (當只輸入 `make` 時)
DEFAULT_GOAL := help

# 從 .env 檔案中讀取變數，並讓它們在 make 指令中可用
# `-include` 會在 .env 檔案不存在時忽略錯誤
-include .env
export

# 指令說明 (透過 make help 顯示)
# 使用 ## 來標記要顯示說明的 target
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Development Setup ---
install: ## Install all dependencies for development
	@echo "Setting up virtual environment and installing all dependencies..."
	@uv venv
	@uv pip install -e '.[auth,expense,dev]'
	@echo "✅ Dependencies installed."

setup-env: ## Create a local .env file from the example
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo "✅ .env file created. Please fill in your secrets."; \
	else \
		echo "✅ .env file already exists."; \
	fi

# --- Running Services ---
run: install ## Run all services concurrently using honcho
	@echo "🚀 Starting all services..."
	@honcho start

run-auth: install ## Run only the auth_service
	@echo "🚀 Starting auth_service on port 8001..."
	@python -m uvicorn services.auth_service.app.main:app --reload --port 8001

run-expense: install ## Run only the expense_service
	@echo "🚀 Starting expense_service on port 8002..."
	@python -m uvicorn services.expense_service.app.main:app --reload --port 8002

db-seed: ## Seed the database with initial data (e.g., default categories)
	@echo "🌱 Seeding database with initial data..."
	@python scripts/seed_database.py
	@echo "✅ Database seeding complete."

# --- Code Quality & Testing ---
lint: install ## Lint and format the codebase with ruff
	@echo "🎨 Checking formatting and linting with ruff..."
	@ruff format .
	@ruff check . --fix
	@echo "✅ Linting and formatting complete."

test: install ## Run all unit tests with pytest
	@echo "🧪 Running tests with pytest..."
	@pytest

# --- Cleanup ---
clean: ## Remove all generated files (venv, pycache, etc.)
	@echo "🧹 Cleaning up project..."
	@rm -rf .venv
	@rm -rf **/__pycache__
	@rm -rf .pytest_cache
	@rm -rf **/.ruff_cache
	@echo "✅ Cleanup complete."