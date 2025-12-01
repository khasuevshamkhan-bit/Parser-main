"""create allowances table

Revision ID: b3539e539fae
Revises: 
Create Date: 2025-01-14 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3539e539fae"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allowances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("npa_name", sa.String(length=512), nullable=False),
        sa.Column("level", sa.String(length=64), nullable=True),
        sa.Column("subjects", sa.JSON(), nullable=True),
        sa.Column("validity_period", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("allowances")
