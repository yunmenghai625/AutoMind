"""Create Phase 5 product system persistence.

Revision ID: 20260913_0008
Revises: 20260912_0007
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0008"
down_revision: str | None = "20260912_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
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
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.add_column("vehicles", sa.Column("vin_last4", sa.String(length=4), nullable=True))
    op.create_foreign_key(
        "fk_vehicles_user_id_users",
        "vehicles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_temp_c", sa.Float(), nullable=False),
        sa.Column("seat_heat_level", sa.Integer(), nullable=False),
        sa.Column("charge_limit_percent", sa.Integer(), nullable=False),
        sa.Column("driving_mode", sa.String(length=20), nullable=False),
        sa.Column("preferences_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.CheckConstraint("preferred_temp_c BETWEEN 16 AND 30", name="ck_preferences_temperature"),
        sa.CheckConstraint("seat_heat_level BETWEEN 0 AND 3", name="ck_preferences_seat_heat"),
        sa.CheckConstraint(
            "charge_limit_percent BETWEEN 50 AND 100",
            name="ck_preferences_charge_limit",
        ),
        sa.CheckConstraint(
            "driving_mode IN ('Comfort', 'Sport', 'Eco')",
            name="ck_preferences_driving_mode",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "vehicle_recalls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=False),
        sa.Column("component", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("consequence", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.CheckConstraint("risk IN ('Low', 'Medium', 'High')", name="ck_vehicle_recalls_risk"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vehicle_id", "external_id", name="ux_vehicle_recalls_external"),
    )
    op.create_index(
        "ix_vehicle_recalls_vehicle_expires",
        "vehicle_recalls",
        ["vehicle_id", "expires_at"],
    )

    op.create_table(
        "vehicle_data_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column("cache_key", sa.String(length=128), nullable=False),
        sa.Column("data_type", sa.String(length=30), nullable=False),
        sa.Column("normalized_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "data_type IN ('vin_decode', 'recalls')", name="ck_vehicle_data_cache_type"
        ),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index(
        "ix_vehicle_data_cache_vehicle_type",
        "vehicle_data_cache",
        ["vehicle_id", "data_type"],
    )
    op.create_index("ix_vehicle_data_cache_expires", "vehicle_data_cache", ["expires_at"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
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
        sa.CheckConstraint("rating IN (-1, 1)", name="ck_feedback_rating"),
        sa.CheckConstraint(
            "run_id IS NOT NULL OR message_id IS NOT NULL", name="ck_feedback_target"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_key", "run_id", name="ux_feedback_subject_run"),
        sa.UniqueConstraint("subject_key", "message_id", name="ux_feedback_subject_message"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])
    op.create_index("ix_feedback_run_created", "feedback", ["run_id", "created_at"])
    op.create_index("ix_feedback_subject_created", "feedback", ["subject_key", "created_at"])

    op.add_column(
        "usage_daily",
        sa.Column("text_requests", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "usage_daily",
        sa.Column("aigc_requests", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE usage_daily SET aigc_requests = requests")
    op.drop_constraint("ck_usage_daily_counts", "usage_daily", type_="check")
    op.create_check_constraint(
        "ck_usage_daily_counts",
        "usage_daily",
        "requests >= 0 AND text_requests >= 0 AND aigc_requests >= 0 "
        "AND tokens >= 0 AND image_calls >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_usage_daily_counts", "usage_daily", type_="check")
    op.create_check_constraint(
        "ck_usage_daily_counts",
        "usage_daily",
        "requests >= 0 AND tokens >= 0 AND image_calls >= 0",
    )
    op.drop_column("usage_daily", "aigc_requests")
    op.drop_column("usage_daily", "text_requests")
    op.drop_index("ix_feedback_subject_created", table_name="feedback")
    op.drop_index("ix_feedback_run_created", table_name="feedback")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_vehicle_data_cache_expires", table_name="vehicle_data_cache")
    op.drop_index("ix_vehicle_data_cache_vehicle_type", table_name="vehicle_data_cache")
    op.drop_table("vehicle_data_cache")
    op.drop_index("ix_vehicle_recalls_vehicle_expires", table_name="vehicle_recalls")
    op.drop_table("vehicle_recalls")
    op.drop_table("user_preferences")
    op.drop_constraint("fk_vehicles_user_id_users", "vehicles", type_="foreignkey")
    op.drop_column("vehicles", "vin_last4")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
