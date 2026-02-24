variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "hnpal"
}

variable "environment" {
  description = "Deployment environment (production, staging)"
  type        = string
  default     = "production"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into EC2. Restrict to your IP in production (e.g. 1.2.3.4/32)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "aws_profile" {
  description = "AWS CLI profile to use for authentication (from ~/.aws/credentials)"
  type        = string
  default     = "hnpal"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair (must already exist in AWS)"
  type        = string
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 30
}

# Story 7.4: Application Secrets (passed to docker-compose.yml via .env)

variable "postgres_password" {
  description = "PostgreSQL password for hnpal user"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for GPT models"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram bot token"
  type        = string
  sensitive   = true
}

variable "telegram_channel_id" {
  description = "Telegram channel ID for bot messages (e.g. @hndigest)"
  type        = string
  sensitive   = true
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}
