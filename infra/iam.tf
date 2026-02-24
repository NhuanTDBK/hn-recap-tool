# ── IAM Policy: S3 Access ─────────────────────────────────────────────────────

resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-s3-access"
  description = "Allow EC2 to read/write the application S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.main.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.main.arn
      }
    ]
  })

  tags = local.common_tags
}

# ── IAM Role: EC2 Assume Role ─────────────────────────────────────────────────

resource "aws_iam_role" "ec2_role" {
  name        = "${var.project_name}-ec2-role"
  description = "IAM role for EC2 instance - grants S3 access via instance profile"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "s3_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# ── IAM Instance Profile ──────────────────────────────────────────────────────

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name

  tags = local.common_tags
}
