#!/bin/bash
# Rolling update script for HackerNews Digest
# Deploys latest code with docker compose v2
# Usage: ./scripts/deploy-update.sh [--skip-migrations] [--branch <name>]

set -euo pipefail

cd /opt/hnpal

echo "=== Starting deployment $(date) ==="

# Parse arguments
SKIP_MIGRATIONS=false
BRANCH="main"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-migrations)
      SKIP_MIGRATIONS=true
      shift
      ;;
    --branch)
      BRANCH="${2:-}"
      if [[ -z "$BRANCH" ]]; then
        echo "ERROR: --branch requires a value"
        exit 1
      fi
      shift 2
      ;;
    *)
      echo "ERROR: Unknown argument: $1"
      exit 1
      ;;
  esac
done

# Sync latest code from origin
echo "Syncing code from origin/${BRANCH}..."
git fetch origin "${BRANCH}"
git reset --hard "origin/${BRANCH}"
git clean -fd

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
