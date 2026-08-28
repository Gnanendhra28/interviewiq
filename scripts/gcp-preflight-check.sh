#!/usr/bin/env bash
set -euo pipefail

echo "========================================================"
echo "InterviewIQ GCP Pre-Deployment Validation Audit"
echo "========================================================"

FAILED=0

# 1. Check gcloud CLI
if command -v gcloud &> /dev/null; then
  echo "[PASS] gcloud CLI is installed."
else
  echo "[FAIL] gcloud CLI is NOT installed or not on PATH."
  FAILED=1
fi

# 2. Check authenticated GCP account
if [ $FAILED -eq 0 ]; then
  ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
  if [ -n "$ACTIVE_ACCOUNT" ]; then
    echo "[PASS] Active GCP Account: $ACTIVE_ACCOUNT"
  else
    echo "[FAIL] No active GCP account authenticated (run 'gcloud auth login')."
    FAILED=1
  fi
fi

# 3. Check active GCP Project ID
if [ $FAILED -eq 0 ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
  if [ -n "$PROJECT_ID" ] && [ "$PROJECT_ID" != "(unset)" ]; then
    echo "[PASS] Active GCP Project: $PROJECT_ID"
  else
    echo "[FAIL] No active GCP project configured (run 'gcloud config set project <PROJECT_ID>')."
    FAILED=1
  fi
fi

# 4. Check Terraform CLI
if command -v terraform &> /dev/null; then
  TF_VERSION=$(terraform version | head -n 1)
  echo "[PASS] Terraform CLI: $TF_VERSION"
else
  echo "[FAIL] Terraform CLI is NOT installed."
  FAILED=1
fi

# 5. Check Docker runtime
if command -v docker &> /dev/null; then
  if docker info &> /dev/null; then
    echo "[PASS] Docker daemon is running."
  else
    echo "[WARN] Docker CLI installed, but daemon is not accessible."
  fi
else
  echo "[FAIL] Docker CLI is NOT installed."
  FAILED=1
fi

echo "========================================================"
if [ $FAILED -eq 0 ]; then
  echo "STATUS: READY FOR GCP INFRASTRUCTURE PROVISIONING"
else
  echo "STATUS: PREFLIGHT BLOCKED — ACTION REQUIRED BEFORE DEPLOYMENT"
fi
echo "========================================================"

exit $FAILED
