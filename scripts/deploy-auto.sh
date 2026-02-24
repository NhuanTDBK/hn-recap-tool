#!/usr/bin/env bash
# Full deployment orchestrator:
# 1) Terraform apply (optional)
# 2) Resolve EC2 public IP
# 3) Sync .env + deploy script to VM
# 4) Run remote docker compose deploy (+ Alembic)
#
# Usage:
#   ./scripts/deploy-auto.sh
#   ./scripts/deploy-auto.sh --skip-infra
#   ./scripts/deploy-auto.sh --skip-migrations
#   ./scripts/deploy-auto.sh --branch main

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT_DIR}/infra"
REMOTE_DIR="/opt/hnpal"
REMOTE_USER="${REMOTE_USER:-ubuntu}"

SKIP_INFRA=false
SKIP_ENV_SYNC=false
SKIP_MIGRATIONS=false
BRANCH="main"
AUTO_APPROVE=true

usage() {
  cat <<EOF
Usage: ./scripts/deploy-auto.sh [options]

Options:
  --skip-infra         Skip terraform apply
  --skip-env-sync      Skip copying local .env to VM
  --skip-migrations    Skip alembic upgrade on remote
  --branch <name>      Git branch to deploy (default: main)
  --no-auto-approve    Run terraform apply without -auto-approve
  -h, --help           Show this help
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Required command not found: ${cmd}"
    exit 1
  fi
}

read_tfvar() {
  local key="$1"
  local fallback="$2"
  local tfvars="${INFRA_DIR}/terraform.tfvars"
  local line value

  if [[ -f "${tfvars}" ]]; then
    line="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "${tfvars}" | tail -n1 || true)"
    if [[ -n "${line}" ]]; then
      value="${line#*=}"
      value="$(echo "${value}" | sed -E 's/[[:space:]]+#.*$//')"
      value="$(echo "${value}" | tr -d '"' | tr -d "'" | xargs)"
      if [[ -n "${value}" ]]; then
        echo "${value}"
        return 0
      fi
    fi
  fi

  echo "${fallback}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-infra)
      SKIP_INFRA=true
      shift
      ;;
    --skip-env-sync)
      SKIP_ENV_SYNC=true
      shift
      ;;
    --skip-migrations)
      SKIP_MIGRATIONS=true
      shift
      ;;
    --branch)
      BRANCH="${2:-}"
      if [[ -z "${BRANCH}" ]]; then
        echo "ERROR: --branch requires a value"
        exit 1
      fi
      shift 2
      ;;
    --no-auto-approve)
      AUTO_APPROVE=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

require_cmd terraform
require_cmd aws
require_cmd ssh
require_cmd scp

AWS_REGION="${AWS_REGION:-$(read_tfvar aws_region ap-southeast-1)}"
AWS_PROFILE="${AWS_PROFILE:-$(read_tfvar aws_profile hnpal)}"
KEY_PAIR_NAME="${KEY_PAIR_NAME:-$(read_tfvar key_pair_name '')}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"

if [[ -z "${KEY_PAIR_NAME}" ]]; then
  echo "ERROR: key_pair_name is empty. Set it in infra/terraform.tfvars or KEY_PAIR_NAME env var."
  exit 1
fi

SSH_KEY_PATH="${SSH_KEY_PATH:-${HOME}/.ssh/${KEY_PAIR_NAME}.pem}"
if [[ ! -f "${SSH_KEY_PATH}" ]]; then
  echo "ERROR: SSH private key not found: ${SSH_KEY_PATH}"
  exit 1
fi

if [[ "${SKIP_INFRA}" != "true" ]]; then
  echo ">>> Running terraform init/apply"
  terraform -chdir="${INFRA_DIR}" init
  if [[ "${AUTO_APPROVE}" == "true" ]]; then
    terraform -chdir="${INFRA_DIR}" apply -auto-approve
  else
    terraform -chdir="${INFRA_DIR}" apply
  fi
fi

INSTANCE_ID="$(terraform -chdir="${INFRA_DIR}" output -raw ec2_instance_id)"
if [[ -z "${INSTANCE_ID}" ]]; then
  echo "ERROR: Could not read ec2_instance_id from terraform outputs."
  exit 1
fi

PUBLIC_IP="$(aws ec2 describe-instances \
  --instance-ids "${INSTANCE_ID}" \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)"

if [[ -z "${PUBLIC_IP}" || "${PUBLIC_IP}" == "None" ]]; then
  echo "ERROR: Could not resolve public IP for instance ${INSTANCE_ID}."
  exit 1
fi

echo ">>> Deploy target: ${REMOTE_USER}@${PUBLIC_IP} (${INSTANCE_ID})"
SSH_OPTS=(-i "${SSH_KEY_PATH}" -o StrictHostKeyChecking=accept-new)

if [[ "${SKIP_ENV_SYNC}" != "true" ]]; then
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: Env file not found: ${ENV_FILE}"
    exit 1
  fi
  echo ">>> Syncing .env"
  scp "${SSH_OPTS[@]}" "${ENV_FILE}" "${REMOTE_USER}@${PUBLIC_IP}:/tmp/hnpal.env"
  ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${PUBLIC_IP}" \
    "sudo -n mv /tmp/hnpal.env '${REMOTE_DIR}/.env' && \
     sudo -n chown ${REMOTE_USER}:${REMOTE_USER} '${REMOTE_DIR}/.env' && \
     sudo -n chmod 600 '${REMOTE_DIR}/.env'"
fi

echo ">>> Syncing deploy script"
scp "${SSH_OPTS[@]}" "${ROOT_DIR}/scripts/deploy-update.sh" "${REMOTE_USER}@${PUBLIC_IP}:/tmp/deploy-update.sh"
ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${PUBLIC_IP}" \
  "sudo -n mv /tmp/deploy-update.sh '${REMOTE_DIR}/scripts/deploy-update.sh' && \
   sudo -n chown ${REMOTE_USER}:${REMOTE_USER} '${REMOTE_DIR}/scripts/deploy-update.sh' && \
   chmod +x '${REMOTE_DIR}/scripts/deploy-update.sh'"

echo ">>> Running remote deploy"
REMOTE_ARGS=("--branch" "${BRANCH}")
if [[ "${SKIP_MIGRATIONS}" == "true" ]]; then
  REMOTE_ARGS+=("--skip-migrations")
fi

ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${PUBLIC_IP}" \
  "cd '${REMOTE_DIR}' && ./scripts/deploy-update.sh ${REMOTE_ARGS[*]}"

echo ">>> Deployment finished"
