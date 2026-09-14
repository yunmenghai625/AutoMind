"""Create Phase 4 multimodal diagnosis persistence.

Revision ID: 20260912_0007
Revises: 20260912_0006
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0007"
down_revision: str | None = "20260912_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usage_daily",
        sa.Column("diagnosis_requests", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_usage_daily_diagnosis_requests",
        "usage_daily",
        "diagnosis_requests >= 0",
    )
    op.create_table(
        "diagnosis_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("original_file_name", sa.String(length=255), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("image_sha256", sa.String(length=64), nullable=False),
        sa.Column("image_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mime_type", sa.String(length=40), nullable=False),
        sa.Column("warning_type", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column(
            "visible_evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("citations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_provider", sa.String(length=80), nullable=False),
        sa.Column("requested_model", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_est_cny", sa.Numeric(12, 6), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_diagnosis_confidence"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_diagnosis_latency"),
        sa.CheckConstraint("cost_est_cny >= 0", name="ck_diagnosis_cost"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_run_id"),
    )
    op.create_index("ix_diagnosis_records_user_id", "diagnosis_records", ["user_id"])
    op.create_index(
        "ix_diagnosis_subject_created",
        "diagnosis_records",
        ["subject_key", "created_at"],
    )
    op.create_index("ix_diagnosis_status_created", "diagnosis_records", ["status", "created_at"])
    op.create_index("ix_diagnosis_provider_model", "diagnosis_records", ["provider", "model"])
    op.create_index("ix_diagnosis_image_expires", "diagnosis_records", ["image_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_diagnosis_image_expires", table_name="diagnosis_records")
    op.drop_index("ix_diagnosis_provider_model", table_name="diagnosis_records")
    op.drop_index("ix_diagnosis_status_created", table_name="diagnosis_records")
    op.drop_index("ix_diagnosis_subject_created", table_name="diagnosis_records")
    op.drop_index("ix_diagnosis_records_user_id", table_name="diagnosis_records")
    op.drop_table("diagnosis_records")
    op.drop_constraint("ck_usage_daily_diagnosis_requests", "usage_daily", type_="check")
    op.drop_column("usage_daily", "diagnosis_requests")
