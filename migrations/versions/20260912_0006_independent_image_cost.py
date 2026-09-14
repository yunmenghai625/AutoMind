"""Track the Phase 3.5 image budget independently.

Revision ID: 20260912_0006
Revises: 20260912_0005
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0006"
down_revision: str | None = "20260912_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "aigc_generations",
        sa.Column(
            "image_cost_est_cny",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_aigc_generations_image_cost",
        "aigc_generations",
        "image_cost_est_cny >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_aigc_generations_image_cost", "aigc_generations", type_="check")
    op.drop_column("aigc_generations", "image_cost_est_cny")
