.PHONY: install db migrate dev test lint format contract

install:            ## create .venv with the locked dependencies (Python 3.15 is fetched by uv when missing)
	uv sync

db:                 ## start PostgreSQL 18 in Docker (port 5432)
	docker compose up -d db

migrate:            ## apply database migrations
	uv run alembic upgrade head

dev:                ## run the API with auto-reload on http://localhost:8000
	uv run uvicorn app.main:app --reload --port 8000

test:               ## run the test suite (needs TEST_DATABASE_URL, see tests/conftest.py)
	uv run pytest

lint:
	uv run ruff check app tests migrations && uv run ruff format --check app tests migrations

format:
	uv run ruff check --fix app tests migrations && uv run ruff format app tests migrations

contract:           ## type-check real responses against the frontend's TypeScript types (needs FRONTEND_TYPES_DIR)
	cd tests/contract && npm install --no-audit --no-fund && cd ../.. && uv run pytest tests/test_contract_typescript.py
