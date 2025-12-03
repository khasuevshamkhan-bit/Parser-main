#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Create an Alembic revision using docker compose.

Usage:
  scripts/create_revision.sh "<message>"
  scripts/create_revision.sh --help

The script will:
  1) Ensure the Postgres database container is running and accepting connections
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

# `docker compose run` does not wait on healthchecks, so guard against races
# where Alembic starts before Postgres finishes initializing.
echo "[1.1/3] Waiting for Postgres to accept connections..."
if ! $COMPOSE_CMD exec -T database sh -c \
  'for _ in $(seq 1 30); do pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" && exit 0; sleep 1; done; exit 1'; then
  echo "Postgres did not become ready in time. Check the database logs." >&2
  exit 1
fi
echo "Postgres is ready."

echo "[2/3] Upgrading database to current head..."
$COMPOSE_CMD run --rm app alembic upgrade head

echo "[3/3] Creating new revision: $REVISION_MESSAGE"
$COMPOSE_CMD run --rm app alembic revision --autogenerate -m "$REVISION_MESSAGE"
