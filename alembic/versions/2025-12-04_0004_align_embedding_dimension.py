"""align embedding column with configured dimension

Revision ID: 5c1f7c8c1c4e
Revises: e30d8f4f2c1b
Create Date: 2025-12-04 00:00:00
"""

from __future__ import annotations

from alembic import op
from pgvector.sqlalchemy import Vector

from src.config import settings

# revision identifiers, used by Alembic.
revision = "5c1f7c8c1c4e"
down_revision = "e30d8f4f2c1b"
branch_labels = None
depends_on = None

# The previous pgvector dimension that may be present in existing databases.
PREVIOUS_DIMENSION = 768


def upgrade() -> None:
    op.execute("TRUNCATE TABLE allowance_embeddings")
    op.alter_column(
        "allowance_embeddings",
        "embedding",
        existing_type=Vector(dim=PREVIOUS_DIMENSION),
        type_=Vector(dim=settings.vector.dimension),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("TRUNCATE TABLE allowance_embeddings")
    op.alter_column(
        "allowance_embeddings",
        "embedding",
        existing_type=Vector(dim=settings.vector.dimension),
        type_=Vector(dim=PREVIOUS_DIMENSION),
        existing_nullable=False,
    )
