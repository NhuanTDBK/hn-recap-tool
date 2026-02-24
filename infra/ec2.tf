# ── AMI: Latest Ubuntu 22.04 LTS ─────────────────────────────────────────────

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── EC2 Instance ──────────────────────────────────────────────────────────────

resource "aws_instance" "main" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.main.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/scripts/user-data.sh", {
    S3_BUCKET_NAME      = aws_s3_bucket.main.id
    AWS_REGION          = var.aws_region
    POSTGRES_PASSWORD   = var.postgres_password
    OPENAI_API_KEY      = var.openai_api_key
    TELEGRAM_BOT_TOKEN  = var.telegram_bot_token
    TELEGRAM_CHANNEL_ID = var.telegram_channel_id
    LOG_LEVEL           = var.log_level
  })

  tags = merge(local.common_tags, { Name = "${var.project_name}-ec2" })
}
