.PHONY: install index index-json

# Install dependencies and generate lock file
install:
	@echo "Installing blog-index dependencies..."
	uv sync

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
