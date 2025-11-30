"""
Create allowances table.

:return: None
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_create_allowances"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Apply allowances table creation.

    :return: None
    """

    op.create_table(
        "allowances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("npa_number", sa.String(length=128), nullable=False),
        sa.Column("subjects", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """
    Revert allowances table creation.

    :return: None
    """

    op.drop_table("allowances")
