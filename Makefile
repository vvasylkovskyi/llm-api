.PHONY: clean install dev-install lint format check db-up db-down db-create migrate migrate-auto rollback index index-db

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Install dependencies
install:
	@echo "Installing dependencies..."
	uv sync

# Install development dependencies
dev-install:
	@echo "Installing development dependencies..."
	uv sync --group dev

# Run linting checks
lint:
	@echo "Running linting checks..."
	uv run python -m ruff check .

lock:
	@echo "Locking dependencies..."
	uv lock

# Format code
format:
	@echo "Formatting code..."
	uv run python -m ruff format .

# Run all checks
check: lint test-coverage
	@echo "All checks completed!"

	.PHONY: run
run:
	@echo "Starting the development server..."
	uv run uvicorn llm_api.main:app --host 0.0.0.0 --port 10000 --reload

# Build the local JSON blog search index (no database required)
index:
	@echo "Building local JSON blog search index..."
	cd blog_index && uv run python main.py \
		--remote-url "$(GITHUB_REMOTE_URL)" \
		--output ../data/blog_index.json

# Index blog posts into Postgres via the blog_index subproject
index-db:
	@echo "Indexing blog posts into Postgres..."
	cd blog_index && uv run python main.py \
		--remote-url "$(GITHUB_REMOTE_URL)" \
		--db

# Start local dev database
db-up:
	@echo "Starting local PostgreSQL..."
	docker compose -f docker-compose.dev.yaml up -d

# Stop local dev database
db-down:
	@echo "Stopping local PostgreSQL..."
	docker compose -f docker-compose.dev.yaml down

# Create the application database if it does not exist
db-create:
	@echo "Creating database if not exists..."
	uv run python -m llm_api.database.create_db

# Apply all pending migrations
migrate:
	@echo "Running Alembic migrations..."
	uv run alembic -c llm_api/database/alembic.ini upgrade head

# Auto-generate a migration (usage: make migrate-auto name=create_my_table)
migrate-auto:
	@echo "Generating migration: $(name)..."
	uv run alembic -c llm_api/database/alembic.ini revision --autogenerate -m "$(name)"

# Rollback last migration
rollback:
	@echo "Rolling back last migration..."
	uv run alembic -c llm_api/database/alembic.ini downgrade -1
