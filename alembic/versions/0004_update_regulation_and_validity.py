"""
Drop npa_number, require npa_name, and add validity_period.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_update_regulation_and_validity"
down_revision = "0003_add_level"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove obsolete NPA number and store validity period."""

    op.execute("UPDATE allowances SET npa_name='' WHERE npa_name IS NULL")

    op.alter_column(
        "allowances",
        "npa_name",
        existing_type=sa.String(length=512),
        nullable=False,
    )

    # Drop npa_number only if it exists to support partially-migrated databases
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("allowances")}
    if "npa_number" in columns:
        op.drop_column("allowances", "npa_number")

    if "validity_period" not in columns:
        op.add_column(
            "allowances",
            sa.Column("validity_period", sa.String(length=128), nullable=True),
        )


def downgrade() -> None:
    """Restore previous schema with npa_number column."""

    op.drop_column("allowances", "validity_period")

    op.add_column(
        "allowances",
        sa.Column("npa_number", sa.String(length=128), nullable=False, server_default=""),
    )
    op.alter_column(
        "allowances",
        "npa_number",
        existing_type=sa.String(length=128),
        nullable=False,
        server_default=None,
    )

    op.alter_column(
        "allowances",
        "npa_name",
        existing_type=sa.String(length=512),
        nullable=True,
    )
