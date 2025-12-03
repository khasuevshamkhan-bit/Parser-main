"""add pgvector embeddings table

Revision ID: d2b66e6f0b1a
Revises: b3539e539fae
Create Date: 2025-03-07 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from src.config import settings

# revision identifiers, used by Alembic.
revision = "d2b66e6f0b1a"
down_revision = "b3539e539fae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "allowance_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("allowance_id", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding", Vector(dim=settings.vector.dimension), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["allowance_id"], ["allowances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allowance_id"),
    )


def downgrade() -> None:
    op.drop_table("allowance_embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
