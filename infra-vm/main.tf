terraform {
  required_version = ">= 1.5"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ── Remote VPS Resource ───────────────────────────────────────────────────────

resource "null_resource" "vps_setup" {
  # Trigger re-provisioning when configuration changes
  triggers = {
    postgres_password   = var.postgres_password
    openai_api_key      = var.openai_api_key
    openai_base_url     = var.openai_base_url
    telegram_bot_token  = var.telegram_bot_token
    telegram_channel_id = var.telegram_channel_id
    app_repo_branch     = var.app_repo_branch
    deploy_script       = filemd5("${path.module}/scripts/deploy-app.sh")
  }

  # Test SSH connection
  provisioner "remote-exec" {
    inline = [
      "echo 'Connected to VPS successfully'",
      "echo 'Hostname: '$(hostname)",
      "echo 'OS: '$(lsb_release -ds)",
      "echo 'Available memory: '$(free -h | awk '/^Mem:/ {print $2}')",
      "echo 'Available disk: '$(df -h / | awk 'NR==2 {print $4}')"
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_user
      host        = var.vps_host
      private_key = var.ssh_private_key_path != "" ? file(pathexpand(var.ssh_private_key_path)) : null
      password    = var.ssh_password != "" ? var.ssh_password : null
      agent       = false
      timeout     = "5m"
    }
  }

  # Setup server dependencies
  provisioner "remote-exec" {
    inline = [
      "set -euo pipefail",
      "echo '=== Installing system dependencies ==='",
      "export DEBIAN_FRONTEND=noninteractive",
      "apt-get update -y",
      "apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git",

      "echo '=== Installing Docker ==='",
      "if ! command -v docker &> /dev/null; then",
      "  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg",
      "  echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | tee /etc/apt/sources.list.d/docker.list > /dev/null",
      "  apt-get update -y",
      "  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
      "  systemctl enable docker",
      "  systemctl start docker",
      "  echo 'Docker installed successfully'",
      "else",
      "  echo 'Docker already installed'",
      "fi",

      "echo '=== Creating application directories ==='",
      "mkdir -p ${var.app_install_path}",
      "mkdir -p ${var.app_data_path}",
      "chown -R ${var.ssh_user}:${var.ssh_user} ${var.app_install_path}",
      "chown -R ${var.ssh_user}:${var.ssh_user} ${var.app_data_path}",

      "echo '=== Cloning/updating application repository ==='",
      "if [ -d ${var.app_install_path}/.git ]; then",
      "  cd ${var.app_install_path}",
      "  git fetch origin",
      "  git checkout ${var.app_repo_branch}",
      "  git pull origin ${var.app_repo_branch}",
      "else",
      "  git clone --branch ${var.app_repo_branch} ${var.app_repo_url} ${var.app_install_path}",
      "fi",

      "echo '=== Creating environment file ==='",
      "cat > ${var.app_install_path}/.env << 'ENVEOF'",
      "DATABASE_URL=postgresql+asyncpg://hn_pal:${var.postgres_password}@postgres:5432/hn_pal",
      "POSTGRES_USER=hn_pal",
      "POSTGRES_PASSWORD=${var.postgres_password}",
      "POSTGRES_DB=hn_pal",
      "REDIS_URL=redis://redis:6379",
      "OPENAI_API_KEY=${var.openai_api_key}",
      "OPENAI_BASE_URL=${var.openai_base_url}",
      "OPENAI_MODEL=gemini-3.6-flash",
      "TELEGRAM_BOT_TOKEN=${var.telegram_bot_token}",
      "TELEGRAM_CHANNEL_ID=${var.telegram_channel_id}",
      "LOG_LEVEL=${var.log_level}",
      "DATA_SOURCE_PATH=${var.app_data_path}",
      "DATA_DIR=${var.app_data_path}",
      "HOST_DATA_DIR=${var.app_data_path}",
      "APP_DATA_DIR=/app/data",
      "LANGFUSE_ENABLED=false",
      "OPENAI_AGENTS_DISABLE_TRACING=1",
      "RESTART_POLICY=unless-stopped",
      "ENVEOF",
      "chmod 600 ${var.app_install_path}/.env",
      "chown ${var.ssh_user}:${var.ssh_user} ${var.app_install_path}/.env",

      "echo '=== System setup completed ==='",
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_user
      host        = var.vps_host
      private_key = var.ssh_private_key_path != "" ? file(pathexpand(var.ssh_private_key_path)) : null
      password    = var.ssh_password != "" ? var.ssh_password : null
      agent       = false
      timeout     = "10m"
    }
  }

  # Deploy application
  provisioner "file" {
    source      = "${path.module}/scripts/deploy-app.sh"
    destination = "/tmp/deploy-app.sh"

    connection {
      type        = "ssh"
      user        = var.ssh_user
      host        = var.vps_host
      private_key = var.ssh_private_key_path != "" ? file(pathexpand(var.ssh_private_key_path)) : null
      password    = var.ssh_password != "" ? var.ssh_password : null
      agent       = false
      timeout     = "5m"
    }
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/deploy-app.sh",
      "APP_INSTALL_PATH=${var.app_install_path} /tmp/deploy-app.sh",
      "rm /tmp/deploy-app.sh"
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_user
      host        = var.vps_host
      private_key = var.ssh_private_key_path != "" ? file(pathexpand(var.ssh_private_key_path)) : null
      password    = var.ssh_password != "" ? var.ssh_password : null
      agent       = false
      timeout     = "15m"
    }
  }
}

# ── Locals ────────────────────────────────────────────────────────────────────

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
