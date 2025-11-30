"""
Add npa_name column to allowances table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_add_npa_name"
down_revision = "0001_create_allowances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add npa_name column.
    """

    op.add_column(
        "allowances",
        sa.Column("npa_name", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    """
    Remove npa_name column.
    """

    op.drop_column("allowances", "npa_name")

