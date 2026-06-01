.PHONY: install db-create migrate rollback index index-json

# Install dependencies and generate lock file
install:
	@echo "Installing blog-index dependencies..."
	uv sync

# Create the viktor_blog database if it does not exist
db-create:
	@echo "Creating viktor_blog database..."
	uv run python create_db.py

# Apply all pending migrations against viktor_blog
migrate:
	@echo "Running blog index migrations..."
	uv run alembic -c alembic.ini upgrade head

# Rollback last migration
rollback:
	@echo "Rolling back last blog index migration..."
	uv run alembic -c alembic.ini downgrade -1

# Index posts into Postgres (requires DATABASE_URL and GITHUB_TOKEN)
index:
	@echo "Indexing blog posts into Postgres..."
	uv run python build_blog_index.py \
		--remote-url "$(GITHUB_REMOTE_URL)" \
		--db

# Build local JSON index (no database required)
index-json:
	@echo "Building local JSON blog index..."
	uv run python build_blog_index.py \
		--remote-url "$(GITHUB_REMOTE_URL)" \
		--output ../data/blog_index.json
