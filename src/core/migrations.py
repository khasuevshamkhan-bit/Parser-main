from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from src.config import settings


def run_migrations() -> None:
    """
    Apply Alembic migrations up to the latest head revision.
    """

    project_root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database.sync_url())
    alembic_cfg.attributes["configure_logger"] = False

    command.upgrade(alembic_cfg, "head")

