# Multi-stage Dockerfile for HackerNews Digest Backend

# Stage 1: Base image with Python and uv
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies + uv
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Stage 2: Production dependencies
FROM base AS dependencies

COPY pyproject.toml uv.lock README.md ./

# Export all deps including dependency-groups (pydantic[email], rocksdict, etc.)
# Filter out editable install (-e .) which requires full source
RUN uv export --frozen --no-hashes -o /tmp/requirements.txt && \
    grep -v "^-e " /tmp/requirements.txt > /tmp/requirements-filtered.txt && \
    pip install --no-cache-dir -r /tmp/requirements-filtered.txt

# Stage 3: Development (same deps, different entrypoint)
FROM dependencies AS development

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 4: Production
FROM dependencies AS production

RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
