#!/bin/bash
set -euo pipefail
exec > /var/log/user-data.log 2>&1

echo "=== Starting EC2 bootstrap $(date) ==="

# System updates
apt-get update -y
apt-get upgrade -y

# Docker (official repo)
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker ubuntu
systemctl enable docker

# s3fs-fuse
apt-get install -y s3fs

# Git
apt-get install -y git

# Mount S3
mkdir -p /mnt/s3data
mkdir -p /tmp/s3cache
s3fs ${S3_BUCKET_NAME} /mnt/s3data \
  -o iam_role=auto \
  -o allow_other \
  -o use_cache=/tmp/s3cache \
  -o url=https://s3.${AWS_REGION}.amazonaws.com

# Persist mount across reboots
echo "${S3_BUCKET_NAME} /mnt/s3data fuse.s3fs _netdev,iam_role=auto,allow_other,use_cache=/tmp/s3cache,url=https://s3.${AWS_REGION}.amazonaws.com 0 0" >> /etc/fstab

# App directory
mkdir -p /opt/hnpal
chown ubuntu:ubuntu /opt/hnpal

# S3 subdirectories
mkdir -p /mnt/s3data/backups
mkdir -p /mnt/s3data/logs
mkdir -p /mnt/s3data/exports

# Clone repository (as ubuntu user for SSH key access)
echo "Cloning repository..."
cd /opt/hnpal
sudo -u ubuntu git clone https://github.com/NhuanTDBK/hn-recap-tool.git . || true

# Create .env file from Terraform-provided secrets
echo "Creating .env file..."
cat > /opt/hnpal/.env << EOF
DATABASE_URL=postgresql+asyncpg://hn_pal:${POSTGRES_PASSWORD}@postgres:5432/hn_pal
POSTGRES_USER=hn_pal
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=hn_pal
REDIS_URL=redis://redis:6379
OPENAI_API_KEY=${OPENAI_API_KEY}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHANNEL_ID=${TELEGRAM_CHANNEL_ID}
LOG_LEVEL=${LOG_LEVEL}
DATA_SOURCE_PATH=/mnt/s3data
DATA_DIR=/mnt/s3data
HOST_DATA_DIR=/mnt/s3data
APP_DATA_DIR=/mnt/s3data
LANGFUSE_ENABLED=false
OPENAI_AGENTS_DISABLE_TRACING=1
EOF
chmod 600 /opt/hnpal/.env
chown ubuntu:ubuntu /opt/hnpal/.env

# Start Docker daemon
systemctl start docker

# Wait for Docker
sleep 5

# Build and start services
echo "Building and starting services..."
cd /opt/hnpal
sudo -u ubuntu docker compose build bot summarizer delivery trigger_posts_collection || true
sudo -u ubuntu docker compose up -d postgres redis bot summarizer delivery trigger_posts_collection

# Run migrations (wait for postgres to be ready)
echo "Running database migrations..."
sleep 10
sudo -u ubuntu docker compose run --rm bot alembic upgrade head || true

echo "=== EC2 bootstrap complete $(date) ==="
