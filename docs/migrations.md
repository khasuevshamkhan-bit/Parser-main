# Running Alembic migrations and revisions

This project expects Alembic to connect to MySQL using the connection values provided via env variables. If `alembic revision --autogenerate` fails, make sure the database is reachable and the env vars are set.

## Quick start inside Docker
1. Start the database container:
   ```bash
   docker compose up -d database
   ```
2. Make sure the app service is up (it runs Alembic on startup):
   ```bash
   docker compose up -d app
   ```
   > If the app container exits because a migration failed, fix the migration and restart `docker compose up -d app` so the revision state matches the DB.
3. Run Alembic from the backend service (service name: `app`). Using the service name works even if the container name is `parser_backend_container`:
   ```bash
   docker compose run --rm app alembic revision --autogenerate -m "<message>"
   ```
   or, if the containers are already running:
   ```bash
   docker compose exec app alembic revision --autogenerate -m "<message>"
   ```
4. If you see `Target database is not up to date`, bring the database to the current head before creating a new revision:
   ```bash
   docker compose run --rm app alembic upgrade head
   ```

## One-command helper script
You can also use the convenience script to create a revision from the project root:

```bash
scripts/create_revision.sh "<message>"
```

The script ensures the database is running, applies pending upgrades, and then calls `alembic revision --autogenerate` inside the `app` service. Set `COMPOSE_CMD` if you need to override the docker compose binary (for example, `COMPOSE_CMD="docker-compose" scripts/create_revision.sh "msg"`).

## Если Alembic приходилось удалять
Чтобы вернуть штатную структуру Alembic, убедитесь, что в проекте присутствуют:

- `alembic.ini` в корне проекта;
- каталог `alembic/` с файлами `env.py`, `script.py.mako` и подпапкой `versions/`.

В этом репозитории уже лежит готовый шаблон (`alembic/script.py.mako`), так что достаточно обновить код до свежей версии. При необходимости можно переинициализировать служебные файлы командой `alembic init alembic` и потом вернуть содержимое `env.py` из репозитория (оно подключает `src` и берет строку подключения из `settings`).

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
