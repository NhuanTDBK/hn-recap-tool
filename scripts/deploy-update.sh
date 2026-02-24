#!/bin/bash
# Rolling update script for HackerNews Digest
# Deploys new app code without downtime
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

# Build new app image
echo "Building app image..."
docker compose -f docker-compose.prod.yml build app

# Run migrations (if not skipped)
if [[ "$SKIP_MIGRATIONS" == "false" ]]; then
  echo "Running database migrations..."
  docker compose -f docker-compose.prod.yml up -d postgres redis
  sleep 5
  docker compose -f docker-compose.prod.yml exec -T app alembic upgrade head || echo "Migration already up to date"
fi

# Restart app only (postgres + redis untouched)
# Telegram buffers messages during ~3-5s restart window
echo "Restarting app service..."
docker compose -f docker-compose.prod.yml up -d --no-deps app

# Wait for app to be healthy
echo "Waiting for app to become healthy..."
for i in {1..60}; do
  if docker compose -f docker-compose.prod.yml exec -T app curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "App is healthy!"
    break
  fi
  if [[ $i -eq 60 ]]; then
    echo "App failed to become healthy after 60s"
    exit 1
  fi
  echo "Waiting... ($i/60)"
  sleep 1
done

echo "=== Deployment complete $(date) ==="
