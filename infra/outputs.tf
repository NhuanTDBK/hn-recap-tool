# Outputs populated progressively across stories
# Story 7.1: Networking
# Story 7.2: S3 + IAM (added there)
# Story 7.3: EC2 (added there)

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.main.id
}

# Story 7.2: S3 + IAM

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.main.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.main.arn
}

output "iam_instance_profile_name" {
  description = "IAM instance profile name (used by EC2 in Story 7.3)"
  value       = aws_iam_instance_profile.ec2_profile.name
}

output "iam_role_arn" {
  description = "IAM role ARN"
  value       = aws_iam_role.ec2_role.arn
}

# Story 7.3: EC2

output "ec2_public_ip" {
  description = "EC2 instance public IP"
  value       = aws_instance.main.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.main.id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${aws_instance.main.public_ip}"
}
