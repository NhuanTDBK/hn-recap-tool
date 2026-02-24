# Epic 7: AWS Infrastructure Deployment

## Overview

Deploy the HackerNews Digest application to AWS using Infrastructure-as-Code (Terraform). This epic transitions the application from local-only development to a cloud-hosted production environment using EC2 for compute, S3 for persistent storage, and Docker Compose for full service orchestration (app + databases).

## Business Value

- Application runs 24/7 in a reliable cloud environment
- Infrastructure is reproducible and version-controlled via Terraform
- Easy teardown/rebuild for cost management (pay only when running)
- Fully Dockerized — consistent across local dev and production
- Foundation for future scaling (larger instances, auto-scaling, etc.)

## Architecture Decision

**Chosen:** AWS EC2 (VM-based) + S3 storage + fully Dockerized
**Alternative considered:** Vercel serverless + Supabase (original plan in tech-stack.md)
**Rationale:** EC2 provides full control over long-running processes (APScheduler daemon, aiogram polling bot, RocksDB embedded storage) which are not well-suited for serverless architectures.

## Target Architecture

```
┌──────────────────────────────────────────────────────┐
│                      AWS Cloud                        │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │               VPC (10.0.0.0/16)                 │ │
│  │                                                  │ │
│  │  ┌──────────────────────────────────────────┐   │ │
│  │  │      Public Subnet (10.0.1.0/24)         │   │ │
│  │  │                                          │   │ │
│  │  │  ┌──────────────────────────────────┐   │   │ │
│  │  │  │      EC2 t3.micro (free tier)    │   │   │ │
│  │  │  │      2 vCPU, 1 GB RAM            │   │   │ │
│  │  │  │      30 GB gp3 EBS               │   │   │ │
│  │  │  │                                  │   │   │ │
│  │  │  │  ┌────────────────────────────┐ │   │   │ │
│  │  │  │  │     Docker Compose         │ │   │   │ │
│  │  │  │  │  ┌──────────────────────┐  │ │   │   │ │
│  │  │  │  │  │  app (hnpal)         │  │ │   │   │ │
│  │  │  │  │  │  - aiogram bot       │  │ │   │   │ │
│  │  │  │  │  │  - APScheduler       │  │ │   │   │ │
│  │  │  │  │  │  - RocksDB           │  │ │   │   │ │
│  │  │  │  │  ├──────────────────────┤  │ │   │   │ │
│  │  │  │  │  │  postgres:15-alpine  │  │ │   │   │ │
│  │  │  │  │  ├──────────────────────┤  │ │   │   │ │
│  │  │  │  │  │  redis:7-alpine      │  │ │   │   │ │
│  │  │  │  │  └──────────────────────┘  │ │   │   │ │
│  │  │  │  └────────────────────────────┘ │   │   │ │
│  │  │  │                                  │   │   │ │
│  │  │  │  /mnt/s3data ────────────────────────► S3  │
│  │  │  │   (s3fs-fuse: backups, logs)     │   │   │ │
│  │  │  └──────────────────────────────────┘   │   │ │
│  │  └──────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  IAM Role (EC2 → S3 access, no hardcoded keys)       │
└──────────────────────────────────────────────────────┘
```

## Prerequisites

1. **AWS Account** with billing enabled
2. **AWS CLI** installed and configured (`aws configure` with Access Key ID + Secret Access Key)
3. **Terraform >= 1.5** installed
4. **SSH Key Pair** created in AWS Console (EC2 → Key Pairs)

### Terraform Authentication

Terraform uses AWS credentials from `~/.aws/credentials` (created by `aws configure`):

```bash
$ aws configure
AWS Access Key ID: AKIA...
AWS Secret Access Key: wJal...
Default region: ap-southeast-1
```

The IAM user needs permissions to create VPC, EC2, S3, and IAM resources. For personal projects, `AdministratorAccess` policy is simplest.

## AWS Resources Created

| Resource | Details |
|----------|---------|
| VPC | 10.0.0.0/16 with internet gateway |
| Public Subnet | 10.0.1.0/24 |
| Security Group | SSH (22), HTTP (80), HTTPS (443) |
| EC2 Instance | t3.micro, Ubuntu 22.04, 30 GB gp3 |
| S3 Bucket | Versioned, encrypted, private |
| IAM Role | EC2 assume-role with S3 read/write |
| Instance Profile | Attaches IAM role to EC2 |

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| EC2 t3.micro | **$0** (free tier: 750 hrs/mo for 12 months) |
| EBS 30 GB gp3 | **$0** (free tier: 30 GB/mo for 12 months) |
| S3 (< 5 GB) | **$0** (free tier: 5 GB for 12 months) |
| Data transfer | ~$0.00 |
| **Year 1 Total** | **$0/mo** (free tier) |
| **After free tier** | **~$7/mo** (t3.micro $6.27 + EBS $2.40 + S3 $0.12) |

## Terraform Project Structure

```
infra/
├── main.tf                  # Provider, VPC, networking
├── s3.tf                    # S3 bucket, lifecycle rules
├── iam.tf                   # IAM role, policy, instance profile
├── ec2.tf                   # EC2 instance, user-data
├── variables.tf             # Input variables
├── outputs.tf               # Output values
├── terraform.tfvars.example # Example config (no secrets)
├── scripts/
│   ├── user-data.sh         # EC2 bootstrap + Docker install + S3 mount
│   └── docker-compose.prod.yml  # Production compose (app + postgres + redis)
└── README.md                # Documentation
```

## Deployment Strategy

**Fully Dockerized** — all services in Docker Compose:
- `app` — Python application (bot + scheduler + RocksDB)
- `postgres` — PostgreSQL 15
- `redis` — Redis 7

**Rolling update** (simple, no over-engineering):
```bash
ssh into EC2
cd /opt/hnpal
git pull
docker compose build app
docker compose up -d --no-deps app
# PostgreSQL + Redis untouched
# Telegram buffers messages during ~3-5s restart
# Zero message loss
```

Bot runs in **polling mode** — Telegram queues messages for offline bots (24-hour buffer), so brief restarts cause zero message loss.

---

## Stories

### Story 7.1: Terraform Foundation & AWS Networking

**Goal:** Set up the Terraform project structure and create the networking foundation (VPC, subnet, internet gateway, security group).

**Acceptance Criteria:**
1. `infra/` directory created with `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`
2. `.gitignore` updated to exclude `.terraform/`, `*.tfstate*`, `terraform.tfvars`
3. AWS provider configured with region variable (default: `ap-southeast-1`)
4. VPC created with CIDR `10.0.0.0/16`
5. Public subnet created with CIDR `10.0.1.0/24` and auto-assign public IP
6. Internet gateway attached to VPC with route table routing `0.0.0.0/0`
7. Security group created with inbound SSH (22, configurable CIDR), HTTP (80), HTTPS (443); outbound all
8. `terraform init` and `terraform plan` succeed without errors

**Dependencies:** None

---

### Story 7.2: S3 Storage & IAM Access Control

**Goal:** Create an S3 bucket for persistent storage and configure IAM so EC2 can access it securely without hardcoded credentials.

**Acceptance Criteria:**
1. S3 bucket created with configurable name (e.g., `hnpal-data-{env}`)
2. Bucket has versioning enabled, server-side encryption (AES-256), and all public access blocked
3. IAM policy created granting `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `s3:DeleteObject` scoped to the bucket
4. IAM role created with EC2 assume-role trust policy
5. Instance profile created and associated with the IAM role
6. `terraform plan` shows S3 + IAM resources correctly

**Dependencies:** Story 7.1 (provider config, variables structure)

---

### Story 7.3: EC2 Provisioning with S3 Mount

**Goal:** Provision an EC2 t3.micro instance with Docker installed and S3 bucket mounted to the filesystem.

**Acceptance Criteria:**
1. EC2 instance created: t3.micro, Ubuntu 22.04 LTS, 30 GB gp3 root volume
2. Instance placed in public subnet with security group and IAM instance profile from prior stories
3. User-data script installs: Docker, Docker Compose v2, s3fs-fuse, git
4. S3 bucket mounted at `/mnt/s3data` using s3fs-fuse with IAM role authentication
5. S3 mount persists across reboots via `/etc/fstab`
6. SSH access works: `ssh -i <key> ubuntu@<public-ip>`
7. `terraform apply` creates all resources; `terraform destroy` cleans them up
8. S3 mount verified: read/write test file from EC2

**Dependencies:** Story 7.1, Story 7.2

---

### Story 7.4: Application Deployment & Service Management

**Goal:** Deploy the fully Dockerized application with zero-message-loss update strategy.

**Acceptance Criteria:**
1. `docker-compose.prod.yml` runs all 3 services: app, PostgreSQL 15, Redis 7
2. App container built from Dockerfile (Python 3.11, uv, application code)
3. PostgreSQL memory-tuned for t3.micro (`shared_buffers=64MB`, `work_mem=4MB`)
4. Application code deployed via git clone to `/opt/hnpal/`
5. Alembic migrations run inside app container on startup
6. Secrets passed via Terraform → `.env` file on EC2 (mode 600) → Docker Compose `env_file`
7. `docker compose up -d` starts all services; auto-restarts on reboot via `restart: unless-stopped`
8. Telegram bot responds to `/start` command (polling mode)
9. Rolling update works: `docker compose up -d --no-deps app` restarts app only, Telegram buffers messages
10. `infra/README.md` documents: prerequisites (AWS CLI, Terraform, key pair), quick start, variable reference, SSH access, deploy/update commands, cost estimates

**Dependencies:** Story 7.3

---

## Key Technical Notes

### Fully Dockerized

All services run in Docker Compose — no systemd service needed for the app:

```yaml
services:
  app:
    build: ./backend
    env_file: .env
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    restart: unless-stopped
    volumes:
      - rocksdb_data:/app/data

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    command: postgres -c shared_buffers=64MB -c work_mem=4MB
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
```

### S3 Mount Usage
- **RocksDB** stays on local EBS (Docker volume) for performance
- S3 mount at `/mnt/s3data/` used for: backups, logs, data exports

### Secrets Flow
```
terraform.tfvars (local, gitignored)
    ↓ terraform apply
EC2 user-data (base64 in instance metadata)
    ↓ bootstrap script
/opt/hnpal/.env (mode 600)
    ↓ docker compose
Container environment variables
```

### Terraform Authentication
```
~/.aws/credentials (via `aws configure`)
    ↓ Terraform auto-detects
provider "aws" { region = var.aws_region }
```
No AWS keys in Terraform files. Never committed to git.
