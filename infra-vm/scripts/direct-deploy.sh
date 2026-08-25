#!/bin/bash
set -euo pipefail

# ══════════════════════════════════════════════════════════════════════════════
# HN Pal - Direct SSH Deployment Script
# ══════════════════════════════════════════════════════════════════════════════
# This script deploys directly via SSH, bypassing Terraform provisioners

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Load variables from terraform.tfvars
VPS_HOST=$(grep '^vps_host' terraform.tfvars | cut -d'=' -f2 | tr -d ' "')
SSH_USER=$(grep '^ssh_user' terraform.tfvars | cut -d'=' -f2 | tr -d ' "' || echo "root")
POSTGRES_PASSWORD=$(grep '^postgres_password' terraform.tfvars | cut -d'=' -f2 | tr -d '"' | xargs)
OPENAI_API_KEY=$(grep '^openai_api_key' terraform.tfvars | cut -d'=' -f2 | tr -d '"' | xargs)
OPENAI_BASE_URL=$(grep '^openai_base_url' terraform.tfvars | cut -d'=' -f2 | tr -d '"' | xargs)
TELEGRAM_BOT_TOKEN=$(grep '^telegram_bot_token' terraform.tfvars | cut -d'=' -f2 | tr -d '"' | xargs)
TELEGRAM_CHANNEL_ID=$(grep '^telegram_channel_id' terraform.tfvars | cut -d'=' -f2 | tr -d '"' | xargs)
APP_REPO_URL=$(grep '^app_repo_url' terraform.tfvars | cut -d'=' -f2 | tr -d '"' | xargs)
APP_REPO_BRANCH=$(grep '^app_repo_branch' terraform.tfvars | cut -d'=' -f2 | tr -d '"' | xargs)

info "Deploying to ${SSH_USER}@${VPS_HOST}"

# Test SSH connection
info "Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 "${SSH_USER}@${VPS_HOST}" "echo 'Connected'" &>/dev/null; then
    error "Cannot connect to ${VPS_HOST}. Check your SSH configuration."
fi
success "SSH connection works"

# Deploy setup script
info "Installing system dependencies..."
ssh "${SSH_USER}@${VPS_HOST}" bash <<'SETUP_EOF'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "=== Updating system ==="
apt-get update -y
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git

echo "=== Installing Docker ==="
if ! command -v docker &> /dev/null; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  echo "Docker installed"
else
  echo "Docker already installed"
fi

echo "=== Creating directories ==="
mkdir -p /opt/hnpal
mkdir -p /opt/hnpal/data
SETUP_EOF

success "System dependencies installed"

# Clone repository
info "Cloning application repository..."
ssh "${SSH_USER}@${VPS_HOST}" bash <<CLONE_EOF
set -euo pipefail

if [ -d /opt/hnpal/.git ]; then
  cd /opt/hnpal
  git fetch origin
  git checkout ${APP_REPO_BRANCH}
  git pull origin ${APP_REPO_BRANCH}
  echo "Repository updated"
else
  git clone --branch ${APP_REPO_BRANCH} ${APP_REPO_URL} /opt/hnpal
  echo "Repository cloned"
fi
CLONE_EOF

success "Repository ready"

# Create .env file
info "Creating environment file..."
ssh "${SSH_USER}@${VPS_HOST}" bash <<ENV_EOF
cat > /opt/hnpal/.env << 'ENVFILE'
DATABASE_URL=postgresql+asyncpg://hn_pal:${POSTGRES_PASSWORD}@postgres:5432/hn_pal
POSTGRES_USER=hn_pal
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=hn_pal
REDIS_URL=redis://redis:6379
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_BASE_URL=${OPENAI_BASE_URL}
OPENAI_MODEL=gemini-3.6-flash
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHANNEL_ID=${TELEGRAM_CHANNEL_ID}
LOG_LEVEL=INFO
DATA_SOURCE_PATH=/opt/hnpal/data
DATA_DIR=/opt/hnpal/data
HOST_DATA_DIR=/opt/hnpal/data
APP_DATA_DIR=/app/data
LANGFUSE_ENABLED=false
OPENAI_AGENTS_DISABLE_TRACING=1
RESTART_POLICY=unless-stopped
ENVFILE
chmod 600 /opt/hnpal/.env
ENV_EOF

success "Environment file created"

# Deploy application
info "Deploying application (this will take 10-15 minutes)..."
scp scripts/deploy-app.sh "${SSH_USER}@${VPS_HOST}:/tmp/deploy-app.sh"
ssh "${SSH_USER}@${VPS_HOST}" bash <<DEPLOY_EOF
chmod +x /tmp/deploy-app.sh
APP_INSTALL_PATH=/opt/hnpal /tmp/deploy-app.sh
rm /tmp/deploy-app.sh
DEPLOY_EOF

success "Deployment completed!"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Deployment Summary"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "VPS Host: ${VPS_HOST}"
echo "Install Path: /opt/hnpal"
echo "Data Path: /opt/hnpal/data"
echo ""
echo "Next steps:"
echo "  1. Check status: ssh ${SSH_USER}@${VPS_HOST} 'cd /opt/hnpal && docker compose ps'"
echo "  2. View logs: ssh ${SSH_USER}@${VPS_HOST} 'cd /opt/hnpal && docker compose logs -f bot'"
echo "  3. Test bot: Send /start to your Telegram bot"
echo ""
