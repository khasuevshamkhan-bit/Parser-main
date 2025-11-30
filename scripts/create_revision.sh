#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Create an Alembic revision using docker compose.

Usage:
  scripts/create_revision.sh "<message>"
  scripts/create_revision.sh --help

The script will:
  1) Ensure the MySQL database container is running
  2) Upgrade the database to the current Alembic head
  3) Create a new autogenerate revision with the provided message
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -eq 0 || -z "${1:-}" ]]; then
  echo "Error: revision message is required." >&2
  echo "" >&2
  usage >&2
  exit 1
fi

REVISION_MESSAGE=$1
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

COMPOSE_CMD=${COMPOSE_CMD:-"docker compose"}

echo "[1/3] Ensuring database service is running..."
$COMPOSE_CMD up -d database

echo "[2/3] Upgrading database to current head..."
$COMPOSE_CMD run --rm app alembic upgrade head

echo "[3/3] Creating new revision: $REVISION_MESSAGE"
$COMPOSE_CMD run --rm app alembic revision --autogenerate -m "$REVISION_MESSAGE"
