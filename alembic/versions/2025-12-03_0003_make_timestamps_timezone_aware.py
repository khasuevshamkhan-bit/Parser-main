"""make timestamps timezone aware

Revision ID: e30d8f4f2c1b
Revises: d2b66e6f0b1a
Create Date: 2025-12-03 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e30d8f4f2c1b"
down_revision = "d2b66e6f0b1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "allowances",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_server_default=sa.func.now(),
        nullable=False,
    )
    op.alter_column(
        "allowance_embeddings",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_server_default=sa.func.now(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "allowance_embeddings",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_server_default=sa.func.now(),
        nullable=False,
    )
    op.alter_column(
        "allowances",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_server_default=sa.func.now(),
        nullable=False,
    )
