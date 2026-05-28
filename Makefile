.PHONY: clean install dev-install lint format check

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
