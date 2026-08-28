#!/usr/bin/env bash
set -euo pipefail

echo "========================================================"
echo "Starting InterviewIQ Database Migration Pipeline"
echo "========================================================"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set." >&2
  exit 1
fi

echo "[MIGRATION] Checking Alembic current revision status..."
PYTHONPATH=. python3 -m alembic -c apps/api/alembic.ini current

echo "[MIGRATION] Upgrading database schema to 'head'..."
PYTHONPATH=. python3 -m alembic -c apps/api/alembic.ini upgrade head

echo "[MIGRATION] Verifying final Alembic schema revision..."
PYTHONPATH=. python3 -m alembic -c apps/api/alembic.ini current

echo "========================================================"
echo "Database Migration Completed Successfully"
echo "========================================================"
