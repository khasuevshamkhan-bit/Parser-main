"""
Add level column to allowances table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_add_level"
down_revision = "0002_add_npa_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add level column for federal/regional distinction.
    """

    op.add_column(
        "allowances",
        sa.Column("level", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """
    Remove level column.
    """

    op.drop_column("allowances", "level")

