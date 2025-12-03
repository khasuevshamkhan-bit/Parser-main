#!/usr/bin/env bash
set -euo pipefail

APP_HOST=${APP_HOST:-0.0.0.0}
APP_PORT=${APP_PORT:-8000}
APP_MODULE=${APP_MODULE:-main:app}

wait_for_db() {
  echo "Waiting for database ${DB_HOST:-localhost}:${DB_PORT:-5432}..."
  for _ in $(seq 1 60); do
    if pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" >/dev/null 2>&1; then
      echo "Database is ready."
      return 0
    fi
    sleep 1
  done
  echo "Database is not ready after waiting; aborting." >&2
  exit 1
}

run_migrations() {
  echo "Applying database migrations..."
  python - <<'PY'
from src.core.migrations import run_migrations

run_migrations()
PY
  echo "Migrations applied."
}

wait_for_db
run_migrations

echo "Starting application..."
exec uvicorn "$APP_MODULE" --host "$APP_HOST" --port "$APP_PORT"
