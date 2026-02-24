#!/bin/bash
# Rolling update script for HackerNews Digest
# Deploys latest code with docker compose v2
# Usage: ./scripts/deploy-update.sh [--skip-migrations]

set -euo pipefail

cd /opt/hnpal

echo "=== Starting deployment $(date) ==="

# Parse arguments
SKIP_MIGRATIONS=false
if [[ "${1:-}" == "--skip-migrations" ]]; then
  SKIP_MIGRATIONS=true
fi

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Build images
echo "Building application images..."
docker compose build bot summarizer delivery trigger_posts_collection

# Run migrations (if not skipped)
if [[ "$SKIP_MIGRATIONS" == "false" ]]; then
  echo "Running database migrations..."
  docker compose up -d postgres redis
  sleep 5
  docker compose run --rm bot alembic upgrade head
fi

# Start all runtime services
echo "Starting services..."
docker compose up -d bot summarizer delivery trigger_posts_collection

echo "Current service status:"
docker compose ps

echo "=== Deployment complete $(date) ==="
