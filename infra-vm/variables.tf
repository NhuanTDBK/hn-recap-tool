variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "hnpal"
}

variable "environment" {
  description = "Deployment environment (production, staging, development)"
  type        = string
  default     = "production"
}

# ── VPS Connection ────────────────────────────────────────────────────────────

variable "vps_host" {
  description = "VPS hostname or IP address (e.g., 'vibe-vm' or '192.168.1.100')"
  type        = string
}

variable "ssh_user" {
  description = "SSH user for VPS access"
  type        = string
  default     = "root"
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key for authentication (leave empty to use password)"
  type        = string
  default     = ""
}

variable "ssh_password" {
  description = "SSH password for authentication (only if not using SSH key)"
  type        = string
  default     = ""
  sensitive   = true
}

# ── Application Paths ─────────────────────────────────────────────────────────

variable "app_install_path" {
  description = "Installation path for application code on VPS"
  type        = string
  default     = "/opt/hnpal"
}

variable "app_data_path" {
  description = "Data directory path for PostgreSQL, RocksDB, logs"
  type        = string
  default     = "/opt/hnpal/data"
}

# ── Application Configuration ─────────────────────────────────────────────────

variable "postgres_password" {
  description = "PostgreSQL password for hnpal user"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "API key for the LLM provider (currently a Gemini key, used via its OpenAI-compatible endpoint)"
  type        = string
  sensitive   = true
}

variable "openai_base_url" {
  description = "Base URL for the OpenAI-compatible LLM endpoint (Gemini's compat endpoint by default)"
  type        = string
  default     = "https://generativelanguage.googleapis.com/v1beta/openai/"
}

variable "telegram_bot_token" {
  description = "Telegram bot token"
  type        = string
  sensitive   = true
}

variable "telegram_channel_id" {
  description = "Telegram channel ID for bot messages"
  type        = string
  sensitive   = true
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "app_repo_url" {
  description = "Git repository URL for the application"
  type        = string
  default     = "https://github.com/NhuanTDBK/hn-recap-tool.git"
}

variable "app_repo_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "main"
}
