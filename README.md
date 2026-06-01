# LLM API Gateway

A production-ready FastAPI microservice for running LLM-powered agents and workflows using LangGraph and the Anthropic Claude API. This service provides a structured gateway for conversational AI agents with built-in observability.

## Overview

This microservice wraps a LangGraph-based agent in a FastAPI server, enabling structured multi-turn conversations powered by Claude Haiku. Beyond AI, the repository demonstrates how to build and deploy an observable LLM API with OpenTelemetry tracing and metrics.

- Fully containerized and ready for deployment
- Built-in OpenTelemetry tracing via Arize Phoenix
- CI/CD with GitHub Actions on a self-hosted Mac runner

## Features

- **LangGraph Agent**: Stateful agent graph with configurable system prompt and message history
- **FastAPI Server**: RESTful API with automatic documentation at `/docs`
- **Anthropic Integration**: Powered by Claude Haiku (`claude-haiku-4-5-20251001`)
- **Observability**: OpenTelemetry tracing (via Arize Phoenix) and OTLP metrics (via Grafana Alloy)
- **Docker Ready**: Containerized with `docker compose` support

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for containerized deployment)
- Anthropic API key

## Local Development

### Installation

```bash
make install
```

### Configuration

Create a `.env` file with the following variables:

```bash
ANTHROPIC_API_KEY=your-api-key-here

# Optional — enable OpenTelemetry instrumentation
ENABLE_INSTRUMENTATION=false
ALLOY_HOST=localhost
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4318/v1/traces
PHOENIX_API_KEY=your-phoenix-api-key
SERVICE_NAME=llm-api
```

### Running Locally

```bash
make run
```

The server starts at `http://localhost:10000`.

## API Endpoints

All routes are prefixed with `/v1`.

### Health Check

```
GET /v1/health-check/
```

Returns service health status.

### Run Agent

```
POST /v1/agent/run
Content-Type: application/json

{
  "messages": [
    { "role": "user", "content": "Your message here" }
  ]
}
```

**Example Request:**

```bash
curl --location 'http://localhost:10000/v1/agent/run' \
--header 'Content-Type: application/json' \
--data '{
  "messages": [
    { "role": "user", "content": "Hello, how are you?" }
  ]
}'
```

**Example Response:**

```json
{
  "status": "OK",
  "response": "I'm doing well, thank you for asking! How can I assist you today?"
}
```

## Docker Deployment

### Using Docker Compose

```bash
docker compose up
```

### Building the Image

```bash
docker build -f Dockerfile -t llm-api:local .
```

### Running the Container

```bash
docker run -d --name llm-api \
  -p 10000:10000 \
  -e ANTHROPIC_API_KEY=your-api-key \
  llm-api:local
```

## CI/CD

The repository includes a GitHub Actions workflow for automated Docker image building, publishing to Docker Hub, and deployment via `docker compose`. See [`.github/workflows/build-on-mac.yml`](.github/workflows/build-on-mac.yml) for details.

### Required Secrets

Set these secrets in your GitHub repository:

- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `ANTHROPIC_API_KEY`

## Blog Knowledge Base

`scripts/build_blog_index.py` fetches `.mdx` blog posts from GitHub and upserts them into a dedicated PostgreSQL database (`viktor_blog`). This database lives on the same self-hosted Postgres server as the application database (`mydb`) but is fully isolated — separate database name, separate connection, separate Alembic migration chain.

Run it manually from GitHub Actions → **Index Blog Posts** → **Run workflow**, or locally:

```bash
DATABASE_URL=postgresql://postgres:pass@100.95.50.80:5432/viktor_blog \
GITHUB_TOKEN=ghp_... \
  uv run python scripts/build_blog_index.py \
    --remote-url https://github.com/vvasylkovskyi/vvasylkovskyi.github.io/tree/main/content/blog \
    --db
```

### Database layout

```mermaid
graph TB
    subgraph pg["PostgreSQL Server — 100.95.50.80:5432"]
        subgraph mydb["mydb  (application database)"]
            app["existing app tables\nalembic_version"]
        end
        subgraph vb["viktor_blog  (blog index database)"]
            bp["blog_posts\n─────────────────────\nslug        TEXT  PK\ntitle       TEXT\ndate        TEXT\ntags        TEXT[]\nexcerpt     TEXT\nbody        TEXT\nupdated_at  TIMESTAMPTZ"]
        end
    end

    scraper["scripts/build_blog_index.py\n--db"] -->|upsert per post| bp
    search["llm_api/search/blog_search.py\nBlogSearch._load()"] -->|SELECT * on startup| bp
```

`BlogSearch` loads all rows into memory at startup and runs BM25 scoring in-process — no query hits Postgres at search time. When `DATABASE_URL` is not set (local dev without Postgres), it falls back to `data/blog_index.json`.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastAPI    │
│   Server    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  LangGraph  │
│   Agent     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Anthropic  │
│ Claude API  │
└─────────────┘
```

### Observability Stack

- **Traces**: Arize Phoenix (via OTLP HTTP) — auto-instruments LangChain and FastAPI
- **Metrics**: Grafana Alloy (via OTLP gRPC) — exports FastAPI metrics every 15 seconds

## Repository

[https://github.com/vvasylkovskyi/llm-api](https://github.com/vvasylkovskyi/llm-api)
