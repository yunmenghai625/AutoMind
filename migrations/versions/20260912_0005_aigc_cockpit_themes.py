"""Create Phase 3.5 AIGC cockpit theme tables.

Revision ID: 20260912_0005
Revises: 20260912_0004
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0005"
down_revision: str | None = "20260912_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_daily",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("user_kind", sa.String(length=20), nullable=False),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_est_cny", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "requests >= 0 AND tokens >= 0 AND image_calls >= 0",
            name="ck_usage_daily_counts",
        ),
        sa.CheckConstraint("cost_est_cny >= 0", name="ck_usage_daily_cost"),
        sa.PrimaryKeyConstraint("date", "subject_key"),
    )
    op.create_index("ix_usage_daily_user_id", "usage_daily", ["user_id"])

    op.create_table(
        "aigc_generations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("user_kind", sa.String(length=20), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("enhanced_prompt", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("image_provider", sa.String(length=80), nullable=True),
        sa.Column("image_model", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_est_cny", sa.Numeric(12, 6), nullable=False),
        sa.Column("output_url", sa.Text(), nullable=True),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("regenerated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("degraded_reason", sa.String(length=80), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_aigc_generations_latency"),
        sa.CheckConstraint("cost_est_cny >= 0", name="ck_aigc_generations_cost"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_aigc_generations_user_id", "aigc_generations", ["user_id"])
    op.create_index(
        "ix_aigc_generations_subject_created",
        "aigc_generations",
        ["subject_key", "created_at"],
    )
    op.create_index("ix_aigc_generations_prompt_hash", "aigc_generations", ["prompt_hash"])
    op.create_index(
        "ix_aigc_generations_status_created", "aigc_generations", ["status", "created_at"]
    )

    op.create_table(
        "cockpit_themes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("theme_spec_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("wallpaper_url", sa.Text(), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("applied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("applied_count >= 0", name="ck_cockpit_themes_applied_count"),
        sa.ForeignKeyConstraint(["generation_id"], ["aigc_generations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_id"),
    )
    op.create_index("ix_cockpit_themes_user_id", "cockpit_themes", ["user_id"])
    op.create_index(
        "ix_cockpit_themes_subject_created",
        "cockpit_themes",
        ["subject_key", "created_at"],
    )
    op.create_index("ix_cockpit_themes_prompt_hash", "cockpit_themes", ["prompt_hash"])


def downgrade() -> None:
    op.drop_index("ix_cockpit_themes_prompt_hash", table_name="cockpit_themes")
    op.drop_index("ix_cockpit_themes_subject_created", table_name="cockpit_themes")
    op.drop_index("ix_cockpit_themes_user_id", table_name="cockpit_themes")
    op.drop_table("cockpit_themes")
    op.drop_index("ix_aigc_generations_status_created", table_name="aigc_generations")
    op.drop_index("ix_aigc_generations_prompt_hash", table_name="aigc_generations")
    op.drop_index("ix_aigc_generations_subject_created", table_name="aigc_generations")
    op.drop_index("ix_aigc_generations_user_id", table_name="aigc_generations")
    op.drop_table("aigc_generations")
    op.drop_index("ix_usage_daily_user_id", table_name="usage_daily")
    op.drop_table("usage_daily")
