# Running Alembic migrations and revisions

This project expects Alembic to connect to MySQL using the connection values provided via environment variables. If `alembic revision --autogenerate` fails, make sure the database is reachable and the env vars are set.

## Quick start inside Docker
1. Start the database container:
   ```bash
   docker compose up -d database
   ```
2. Run Alembic from the backend container so it reuses the same settings:
   ```bash
   docker compose run --rm backend_container alembic revision --autogenerate -m "<message>"
   ```
   or, if the containers are already running:
   ```bash
   docker compose exec backend_container alembic revision --autogenerate -m "<message>"
   ```

## Running Alembic directly on the host
1. Ensure MySQL is running and reachable from your host. For the default docker-compose setup, that usually means `DB_HOST=127.0.0.1` and `DB_PORT=3306`.
2. Export the same credentials that the app uses (see `.env`):
   ```bash
   export DB_NAME=...
   export DB_USER=...
   export DB_PASSWORD=...
   export DB_HOST=127.0.0.1
   export DB_PORT=3306
   ```
3. Set the Python path so `src` can be imported:
   ```bash
   export PYTHONPATH=.
   ```
4. Run the revision command:
   ```bash
   alembic revision --autogenerate -m "<message>"
   ```

## Common errors
- **`ModuleNotFoundError: No module named 'src'`** — set `PYTHONPATH=.` (the Alembic `env.py` also inserts the project root, but the env var avoids IDE/terminal drift).
- **`OperationalError: Access denied`** — verify `DB_USER`/`DB_PASSWORD` and that MySQL accepts connections from your host.
- **Duplicate column errors during `upgrade`** — the migrations are written to be idempotent, but if a column already exists, check that you are on the latest code and that your DB schema matches the applied revision history.
