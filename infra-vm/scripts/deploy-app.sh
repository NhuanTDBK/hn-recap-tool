#!/bin/bash
set -euo pipefail

echo "=== Starting HN Pal Application Deployment $(date) ==="

# Application directory from environment or default
APP_DIR="${APP_INSTALL_PATH:-/opt/hnpal}"
DATA_DIR="${APP_INSTALL_PATH:-/opt/hnpal}/data"

# Navigate to application directory
cd "$APP_DIR"

# Verify .env file exists
if [ ! -f "$APP_DIR/.env" ]; then
  echo "ERROR: .env file not found at $APP_DIR/.env"
  exit 1
fi

# Stop existing services (if any)
echo "Stopping existing services..."
docker compose down || true

# Build Docker images
echo "Building Docker images..."
docker compose build bot scheduler

# Start services
echo "Starting services..."
docker compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0
until docker compose exec -T postgres pg_isready -U hn_pal > /dev/null 2>&1; do
  ATTEMPT=$((ATTEMPT + 1))
  if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
    echo "ERROR: PostgreSQL failed to start after $MAX_ATTEMPTS attempts"
    docker compose logs postgres
    exit 1
  fi
  echo "Waiting for PostgreSQL... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
  sleep 2
done

echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
docker compose run --rm bot alembic upgrade head

# Start application services
echo "Starting application services..."
docker compose up -d bot scheduler

# Verify services are running
echo "Verifying services..."
sleep 5
docker compose ps

# Show logs
echo ""
echo "Recent logs:"
docker compose logs --tail=20

echo ""
echo "=== Deployment completed successfully $(date) ==="
echo ""
echo "Services are running at: $APP_DIR"
echo ""
echo "Useful commands:"
echo "  cd $APP_DIR && docker compose ps              # Check service status"
echo "  cd $APP_DIR && docker compose logs -f         # View all logs"
echo "  cd $APP_DIR && docker compose logs -f bot     # View bot logs only"
echo "  cd $APP_DIR && docker compose restart         # Restart all services"
echo ""
