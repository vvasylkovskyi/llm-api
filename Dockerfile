FROM python:3.12-slim

WORKDIR /app

# Install build tools required by llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml and install dependencies with uv
COPY pyproject.toml ./

# Install Python deps
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"

COPY . .
CMD ["uvicorn", "llm_api.main:app", "--host", "0.0.0.0", "--port", "10000"]

