"""Create service metadata table.

Revision ID: 20260912_0001
Revises:
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_metadata",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.execute(
        sa.text("INSERT INTO service_metadata (key, value) VALUES ('schema_version', 'phase-0')")
    )


def downgrade() -> None:
    op.drop_table("service_metadata")
